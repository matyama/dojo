use bb8_redis::{bb8, RedisConnectionManager};
use derive_new::new;
use futures::future::try_join;
use maplit::hashmap;
use redis::streams::{StreamId, StreamKey, StreamReadOptions, StreamReadReply};
use redis::AsyncCommands;
use tracing::{debug, info, warn};

use std::collections::HashMap;
use std::env;
use std::time::Duration;

use redis_stream_wc::{send, Message, DEAULT_REDIS_URL, DEAULT_STREAM_ID};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    tracing_subscriber::fmt::init();

    let stream_key = env::var("STREAM_ID").unwrap_or_else(|_| {
        warn!("STREAM_ID not provided, using default {}", DEAULT_STREAM_ID);
        DEAULT_STREAM_ID.to_owned()
    });

    let shutdown_delay = env::var("SHUTDOWN_DELAY")
        .map(|secs| Duration::from_secs(secs.parse().expect("delay in seconds")));

    let redis_url = env::var("REDIS_URL").unwrap_or_else(|_| {
        warn!("REDIS_URL not provided, using default {}", DEAULT_REDIS_URL);
        DEAULT_REDIS_URL.to_owned()
    });

    // Note: This is just an example of connection pooling. In this particular case it's not
    // actually necessary.
    let manager = RedisConnectionManager::new(redis_url)?;
    let pool = bb8::Pool::builder().max_size(4).build(manager).await?;

    // get dedicated connection for consumig incomming messages
    let mut stream_conn = pool.dedicated_connection().await?;

    info!("Starting counter on stream '{}'...", &stream_key);
    let mut counter = Box::new(Counter::new(pool.clone()));

    // buffer messages to reduce network communication and block current thread execution until new
    // messages arrive
    let opts = StreamReadOptions::default().count(64).block(0);

    // next message offset, alwarys start from the beginning
    let mut stream_state = hashmap! {
        stream_key.clone() => "0-0".to_owned(),
    };

    // spawn interrupt handler
    let interrupt_pool = pool.clone();
    let interrupt_steam = stream_key.clone();
    tokio::spawn(async move {
        if let Ok(()) = tokio::signal::ctrl_c().await {
            info!("Initiating shutdown...");
            send(&interrupt_pool, interrupt_steam, Message::Terminate).await;
        }
    });

    if let Ok(delay) = shutdown_delay {
        tokio::spawn(async move {
            info!("Scheduing shutdown in {}s", delay.as_millis() / 1000);
            tokio::time::sleep(delay).await;
            info!("Initiating shutdown...");
            send(&pool, stream_key.clone(), Message::Terminate).await;
        });
    }

    'stream: loop {
        let (keys, ids): (Vec<&String>, Vec<&String>) = stream_state.iter().unzip();
        let reply: StreamReadReply = stream_conn.xread_options(&keys, &ids, &opts).await?;

        let messages = reply.keys.into_iter().flat_map(|StreamKey { key, ids }| {
            ids.into_iter()
                .map(move |StreamId { id, map }| (key.clone(), id, Message::try_from(map)))
        });

        for (key, id, msg) in messages {
            stream_state.insert(key, id);

            match msg {
                Ok(msg) => {
                    if let Progress::Terminate = counter.handle(msg).await {
                        info!("Counter terminated: {:?}", counter.state());
                        break 'stream;
                    }
                }
                Err(err) => warn!("SKIP: invalid message {}", err),
            }
        }
    }

    Ok(())
}

#[allow(dead_code)]
enum Progress {
    Continue,
    Terminate,
}

const STATE_KEY: &str = "state";
const VERSION_KEY: &str = "version";

#[derive(new)]
struct Counter {
    // alternatively this could use a trie
    #[new(default)]
    state: HashMap<String, usize>,
    pool: bb8::Pool<RedisConnectionManager>,
}

impl Counter {
    #[inline]
    fn state(&self) -> &HashMap<String, usize> {
        &self.state
    }

    #[inline]
    fn as_checkpoint(&self) -> Vec<(String, usize)> {
        self.state.iter().map(|(w, c)| (w.clone(), *c)).collect()
    }

    fn update(&mut self, data: String) {
        for w in data.split_whitespace().map(|w| w.to_lowercase()) {
            *self.state.entry(w).or_default() += 1;
        }
    }

    async fn handle(&mut self, msg: Message) -> Progress {
        debug!("Received message {:?}", &msg);

        match msg {
            Message::Count { client_id, data } => {
                debug!(
                    "Counting words form client '{}' input: '{}'",
                    client_id, &data
                );
                self.update(data);
            }

            Message::Disconnect { client_id } => {
                debug!(
                    "Client '{}' disconnected, checkpointing state: {:?}...",
                    client_id, &self.state
                );

                // save current state and increment checkpoint counter
                self.checkpoint(true).await;
            }

            Message::Terminate => {
                debug!(
                    "Shutdown signal received, saving final checkpoint: {:?}",
                    &self.state
                );
                // save current state but don't increment checkpoint counter
                self.checkpoint(false).await;
                return Progress::Terminate;
            }
        }

        Progress::Continue
    }

    async fn checkpoint(&mut self, inc_count: bool) {
        let pool = self.pool.clone();

        let state = self.as_checkpoint();

        let store_handle = tokio::spawn(async move {
            if !state.is_empty() {
                let mut conn = pool.get().await.expect("Redis connection");
                let _: () = conn
                    .hset_multiple(STATE_KEY, &state)
                    .await
                    .unwrap_or_else(|_| panic!("HSETALL {} state", STATE_KEY));
            }
        });

        let pool = self.pool.clone();

        let counter_handle = tokio::spawn(async move {
            if !inc_count {
                return;
            }
            let mut conn = pool.get().await.expect("Redis connection");
            let _: () = conn.incr(VERSION_KEY, 1).await.expect("INCR version");
        });

        // Note: actually it'd be better to run both commands in a TX
        try_join(store_handle, counter_handle)
            .await
            .expect("checkpoint successful");
    }
}
