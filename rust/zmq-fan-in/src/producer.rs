use std::time::Duration;

use futures::SinkExt;
use tokio::time::sleep;

use log::info;

use std::env;
use tmq::{push, Context, Result};

const DEFAULT_SINK_URL: &str = "tcp://127.0.0.1:6000";

#[tokio::main]
async fn main() -> Result<()> {
    let producer_id = std::env::args().nth(1).expect("no producer ID given");

    if let Err(_) = env::var("RUST_LOG") {
        env::set_var("RUST_LOG", "subscribe=DEBUG");
    }

    pretty_env_logger::init();

    let endpoint = match env::var("SINK_URL") {
        Ok(url) => {
            info!("[{}] Producing to '{}'", producer_id, url);
            url
        }
        Err(_) => {
            info!(
                "[{}] SINK_URL not set, producing to '{}'",
                producer_id, DEFAULT_SINK_URL
            );
            DEFAULT_SINK_URL.to_owned()
        }
    };

    let ctx = Context::new();

    let mut socket = push(&ctx).connect(&endpoint)?;

    let mut i = 0;
    loop {
        let message = format!("[{}] Push #{}", &producer_id, i);
        i += 1;

        info!("Push: {}", message);
        let multipart = vec![message.as_bytes()];
        socket.send(multipart).await?;
        sleep(Duration::from_millis(1000)).await;
    }
}
