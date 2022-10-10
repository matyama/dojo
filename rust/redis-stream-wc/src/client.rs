use bb8_redis::{bb8, RedisConnectionManager};
use tracing::{debug, info, warn};

use std::env;

use redis_stream_wc::{send, Message, DEAULT_REDIS_URL, DEAULT_STREAM_ID};

const DEFAULT_REPEATS: usize = 10;
const DEFAULT_DATA: &str = "hello world";

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();

    let repeats: usize = env::var("REPEATS").map_or_else(
        |_| {
            warn!("REPEATS not provided, defaulting to {}", DEFAULT_REPEATS);
            DEFAULT_REPEATS
        },
        |r| r.parse().unwrap_or(DEFAULT_REPEATS),
    );

    let client_id = env::var("CLIENT_ID").unwrap_or_else(|_| {
        warn!("CLIENT_ID not provided, defaulting to PID");
        format!("client-{}", std::process::id())
    });

    info!("Starting client '{}'...", &client_id);

    let counter_addr = env::var("STREAM_ID").unwrap_or_else(|_| {
        warn!("STREAM_ID not provided, using default {}", DEAULT_STREAM_ID);
        DEAULT_STREAM_ID.to_owned()
    });

    let redis_url = env::var("REDIS_URL").unwrap_or_else(|_| {
        warn!("REDIS_URL not provided, using default {}", DEAULT_REDIS_URL);
        DEAULT_REDIS_URL.to_owned()
    });

    // Note: This is just an example of connection pooling. In this particular case it's not
    // actually necessary.
    let manager = RedisConnectionManager::new(redis_url)?;
    let pool = bb8::Pool::builder().max_size(1).build(manager).await?;

    let data = DEFAULT_DATA.to_owned();
    info!(
        "Client '{}' sending ({}x): '{}'",
        &client_id, &repeats, &data
    );

    for _ in 0..repeats {
        let msg = Message::Count {
            client_id: client_id.clone(),
            data: data.clone(),
        };
        debug!("Client '{}' seding: {:?}", &client_id, &msg);
        send(&pool, counter_addr.clone(), msg).await;
    }

    info!(
        "Client '{}' is disconnecing from '{}'...",
        &client_id, &counter_addr
    );
    send(
        &pool,
        counter_addr.clone(),
        Message::Disconnect {
            client_id: client_id.clone(),
        },
    )
    .await;

    info!("Client '{}' terminated", client_id);
    Ok(())
}
