use axum::{
    async_trait,
    extract::{Extension, FromRequest, Query, RequestParts},
    http::StatusCode,
    response::IntoResponse,
    routing::{get, put},
    Json, Router,
};
use derive_new::new;
use itertools::Itertools;
use petgraph::prelude::Graph;
use redis::{cmd, RedisError};
use redis_graph::*;
use serde::{Deserialize, Serialize};
use std::net::SocketAddr;
use tokio::signal;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

const DUNGEON: &str = "dungeon";

#[derive(Debug, Clone, Deserialize, Default)]
struct RedisConfig {
    #[serde(default = "default_redis_url")]
    url: String,
}

const DEFAULT_REDIS_URL: &str = "redis://127.0.0.1:6379/";
#[inline(always)]
fn default_redis_url() -> String {
    DEFAULT_REDIS_URL.to_string()
}

#[derive(Debug, Deserialize)]
struct Config {
    #[serde(default = "default_rust_log")]
    rust_log: String,
    #[serde(default = "default_server_port")]
    server_port: u16,
    #[serde(default)]
    redis: RedisConfig,
}

const DEFAULT_RUST_LOG: &str = "server=debug";
#[inline(always)]
fn default_rust_log() -> String {
    DEFAULT_RUST_LOG.to_string()
}

const DEFAULT_SERVER_PORT: u16 = 3000;
const fn default_server_port() -> u16 {
    DEFAULT_SERVER_PORT
}

impl Config {
    pub fn from_env() -> Result<Self, config::ConfigError> {
        config::Config::builder()
            .add_source(config::Environment::default().separator("__"))
            .build()?
            .try_deserialize()
    }
}

#[repr(transparent)]
struct RedisConn(redis::aio::Connection);

#[async_trait]
impl<B> FromRequest<B> for RedisConn
where
    B: Send,
{
    type Rejection = (StatusCode, String);

    async fn from_request(req: &mut RequestParts<B>) -> Result<Self, Self::Rejection> {
        let Extension(client) = Extension::<redis::Client>::from_request(req)
            .await
            .map_err(internal_error)?;

        let conn = client
            .get_async_connection()
            .await
            .map_err(internal_error)?;

        Ok(Self(conn))
    }
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "lowercase")]
enum Response<T> {
    Data(T),
    Error(String),
}

#[inline]
fn internal_error<E>(err: E) -> (StatusCode, String)
where
    E: std::error::Error,
{
    (StatusCode::INTERNAL_SERVER_ERROR, err.to_string())
}

#[tokio::main]
async fn main() {
    // load env config
    let cfg = Config::from_env().unwrap();

    // setup tracing
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(cfg.rust_log))
        .with(tracing_subscriber::fmt::layer())
        .init();

    // create Redis client
    // TODO: connection pooling (use deadpool_redis)

    tracing::debug!("connecting to Redis at '{}'", cfg.redis.url);
    let client = redis::Client::open(cfg.redis.url).expect("Redis client");

    // setup request routing with shared Redis pool
    let app = Router::new()
        .route("/", get(health))
        .route("/crawl", get(crawl))
        .route("/dungeon", put(make_dungeon))
        .layer(Extension(client));

    let addr = SocketAddr::from(([0, 0, 0, 0], cfg.server_port));

    // run the app with hyper
    tracing::debug!("listening on {}", addr);

    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .with_graceful_shutdown(shutdown_signal())
        .await
        .unwrap();
}

async fn shutdown_signal() {
    let ctrl_c = async {
        signal::ctrl_c()
            .await
            .expect("failed to install Ctrl+C handler");
    };

    #[cfg(unix)]
    let terminate = async {
        signal::unix::signal(signal::unix::SignalKind::terminate())
            .expect("failed to install signal handler")
            .recv()
            .await;
    };

    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }

    tracing::warn!("signal received, starting graceful shutdown");
}

#[derive(Serialize)]
enum Status {
    Ok,
    Err,
}

#[derive(Serialize)]
struct Health {
    server: Status,
    redis: Status,
}

async fn health(Extension(client): Extension<redis::Client>) -> impl IntoResponse {
    // check redis
    // TODO: replace unwrap with redis: Status::Err
    let mut conn = client.get_async_connection().await.unwrap();
    let reply: Result<String, RedisError> = cmd("PING").query_async(&mut conn).await;

    let redis = match reply {
        Ok(reply) if reply == "PONG" => Status::Ok,
        _ => Status::Err,
    };

    let health = Health {
        server: Status::Ok,
        redis,
    };

    (StatusCode::OK, Json(health))
}

#[derive(Debug, Deserialize)]
struct DungeonParams {
    #[serde(default = "default_size")]
    size: u16,
    #[serde(default = "default_maxgp")]
    maxgp: u32,
    #[serde(default = "default_max_treasures")]
    max_treasures: u8,
}

const DEFAULT_SIZE: u16 = 10;
const fn default_size() -> u16 {
    DEFAULT_SIZE
}

const DEFAULT_MAXGP: u32 = 10;
const fn default_maxgp() -> u32 {
    DEFAULT_MAXGP
}

const DEFAULT_MAX_TREASURES: u8 = 2;
const fn default_max_treasures() -> u8 {
    DEFAULT_MAX_TREASURES
}

#[derive(Debug, Clone, new)]
struct Room {
    id: u16,
}

#[derive(Debug, Clone, new)]
struct Treasure {
    id: u8,
    #[allow(dead_code)]
    gp: u32,
}

async fn make_dungeon(
    RedisConn(mut conn): RedisConn,
    Query(params): Query<DungeonParams>,
) -> impl IntoResponse {
    if params.size == 0 {
        return (
            StatusCode::BAD_REQUEST,
            "'size' must be positive".to_string(),
        );
    }

    if params.maxgp == 0 {
        return (
            StatusCode::BAD_REQUEST,
            "'maxgp' must be positive".to_string(),
        );
    }

    // clear current dungeon graph
    let res: Result<GraphResultSet, RedisError> =
        conn.graph_query(DUNGEON, "MATCH (n) DETACH DELETE n").await;

    if let Err(e) = res {
        return internal_error(e);
    }

    // pick the number of treasures
    let treasure_cnt = fastrand::u8(2..params.max_treasures);

    // create new dungeon grapth
    tracing::info!(
        "generating new dungeon with {} rooms, {} treasures and gp limit of {}",
        params.size,
        treasure_cnt,
        params.maxgp
    );

    // generate random graph of rooms
    let size = params.size as usize;
    let mut graph: Graph<Room, ()> = Graph::with_capacity(size, 2 * size * (size - 1));

    let rooms = (0..params.size)
        .map(Room::new)
        .map(|r| graph.add_node(r))
        .collect_vec();

    // start with complete graph (in both directions)
    let mut corridors = Vec::with_capacity(size * (size - 1));
    for (&r1, &r2) in rooms.iter().tuple_combinations() {
        let c = graph.add_edge(r1, r2, ());
        corridors.push(c);
    }

    // filter out random edges (don't discinnect)
    while graph.edge_count() > 2 * size {
        let i = fastrand::usize(..corridors.len());
        let c = corridors[i];

        if let Some((s, t)) = graph.edge_endpoints(c) {
            let s_out = graph.neighbors(s).count();
            let t_in = graph.neighbors(t).count();
            if s_out > 1 && t_in > 1 {
                graph.remove_edge(c);
            }
        }
    }

    let create_rooms = rooms
        .iter()
        .map(|&n| &graph[n])
        .map(|r| format!("CREATE (r{}:{:?})", r.id, r));

    let create_corridors = graph
        .edge_indices()
        .filter_map(|e| graph.edge_endpoints(e))
        .map(|(s, t)| (&graph[s], &graph[t]))
        .flat_map(|(r1, r2)| {
            let c12 = format!("CREATE (r{})-[:LEADS_TO]->(r{})", r1.id, r2.id);
            let c21 = format!("CREATE (r{})-[:LEADS_TO]->(r{})", r2.id, r1.id);
            [c12, c21].into_iter()
        });

    // generate some treasures
    let treasures = (0..treasure_cnt)
        .map(|id| Treasure::new(id, fastrand::u32(1..params.maxgp)))
        .collect_vec();

    let create_treasures = treasures
        .iter()
        .map(|t| format!("CREATE (t{}:{:?})", t.id, t));

    // place treasures randomly to rooms
    let place_treasures = treasures
        .iter()
        .map(|t| {
            let i = fastrand::usize(..size);
            let r = rooms[i];
            (graph[r].id, t.id)
        })
        .map(|(r, t)| format!("CREATE (r{})-[:CONTAINS]->(t{})", r, t));

    // construct query
    let query = create_rooms
        .chain(create_corridors)
        .chain(create_treasures)
        .chain(place_treasures)
        .join("\n");

    let res: Result<GraphResultSet, RedisError> = conn.graph_query(DUNGEON, query).await;

    match res {
        Ok(_) => (StatusCode::CREATED, String::new()),
        Err(e) => internal_error(e),
    }
}

/// the output of `crawl` handler
#[derive(Default, Serialize)]
struct Crawl {
    // TODO: path: Vec<u16> or better Vec<(Room, Option<Treasure>)>
    /// the shortest path to the largest treasure in the dungeon
    path: String,
    /// total gp collected along the path
    gp: u32,
}

async fn crawl(RedisConn(mut conn): RedisConn) -> impl IntoResponse {
    // TODO: return the total treasure gp on the path
    // TODO: entrance/start is currenlty hard-coded
    //  => generate special :Entrance node or take start as param
    let query = r#"
		MATCH (max:Treasure)
		  WITH max(max.gp) AS maxgp
		MATCH (r:Room)-[:CONTAINS]->(t:Treasure)
		  WHERE t.gp = maxgp
		  WITH r.id AS dest_id
		MATCH (start:Room), (stop:Room)
		  WHERE start.id = 1 AND stop.id = dest_id
		RETURN shortestPath((start)-[:LEADS_TO*]->(stop)) AS path
	"#;

    let res: Result<GraphResultSet, RedisError> = conn.graph_ro_query(DUNGEON, query).await;

    match res {
        Ok(res) => {
            if let Some(path_match) = res.data.first() {
                if let Some(raw_path) = path_match.get_scalar("path") {
                    tracing::info!("treasure path found: {}", raw_path);

                    // TODO: parse raw path into `Room`s
                    // TODO: return total gp
                    let crawl = Crawl {
                        path: raw_path,
                        gp: 0,
                    };

                    return (StatusCode::OK, Json(Response::Data(crawl)));
                }
            }

            tracing::info!("no path from dungeon entrance to the largest treasure");
            (
                StatusCode::NOT_FOUND,
                Json(Response::Data(Crawl::default())),
            )
        }
        Err(e) => (
            StatusCode::INTERNAL_SERVER_ERROR,
            Json(Response::Error(e.to_string())),
        ),
    }
}
