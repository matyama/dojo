use futures::StreamExt;

use log::info;

use std::env;
use tmq::{pull, Context, Result};

const DEFAULT_SINK_URL: &str = "tcp://127.0.0.1:6000";

#[tokio::main]
async fn main() -> Result<()> {
    if let Err(_) = env::var("RUST_LOG") {
        env::set_var("RUST_LOG", "subscribe=DEBUG");
    }

    pretty_env_logger::init();

    let endpoint = match env::var("SINK_URL") {
        Ok(url) => {
            info!("Collecting at '{}'", url);
            url
        }
        Err(_) => {
            info!("SINK_URL not set, collecting at '{}'", DEFAULT_SINK_URL);
            DEFAULT_SINK_URL.to_owned()
        }
    };

    let ctx = Context::new();

    let mut socket = pull(&ctx).bind(&endpoint)?;

    while let Some(msg) = socket.next().await {
        info!(
            "Pull: {:?}",
            msg?.iter()
                .map(|item| item.as_str().unwrap_or("invalid text"))
                .collect::<Vec<&str>>()
        );
    }

    Ok(())
}
