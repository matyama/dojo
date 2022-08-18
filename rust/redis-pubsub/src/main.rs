use futures_util::StreamExt as _;
use redis::AsyncCommands;

use log::info;

use std::env;

#[inline(always)]
fn inbox(replica_id: usize) -> String {
    format!("inbox-{}", replica_id)
}

#[tokio::main]
async fn main() -> redis::RedisResult<()> {
    if let Err(_) = env::var("RUST_LOG") {
        env::set_var("RUST_LOG", "subscribe=DEBUG");
    }

    pretty_env_logger::init();

    let replica_id: usize = env::var("REPLICA_ID")
        .expect("REPLICA_ID to be set")
        .parse()
        .expect("REPLICA_ID to be valid");

    let redis_url = env::var("REDIS_URL").expect("REDIS_URL to be set");

    let client = redis::Client::open(redis_url).unwrap();

    let mut publish_conn = client.get_async_connection().await?;
    let mut pubsub_conn = client.get_async_connection().await?.into_pubsub();

    pubsub_conn.subscribe(inbox(replica_id)).await?;
    let mut pubsub_stream = pubsub_conn.on_message();

    for recipient in (0..replica_id).map(inbox) {
        publish_conn.publish(recipient, replica_id).await?;
    }

    while let Some(msg) = pubsub_stream.next().await {
        let i: usize = msg.get_payload()?;
        info!("registered {}", i);
    }

    Ok(())
}
