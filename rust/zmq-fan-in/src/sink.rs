use futures::StreamExt;

use log::info;

use prost::Message;
use std::io::Cursor;

use std::env;
use tmq::{pull, Context};

const DEFAULT_SINK_URL: &str = "tcp://127.0.0.1:6000";

pub mod msg {
    include!(concat!(env!("OUT_DIR"), "/msg.rs"));
}

impl TryFrom<tmq::Message> for msg::ProducerMessage {
    type Error = prost::DecodeError;

    fn try_from(msg: tmq::Message) -> Result<Self, prost::DecodeError> {
        Self::decode(&mut Cursor::new(&msg[..]))
    }
}

#[tokio::main]
async fn main() -> tmq::Result<()> {
    if let Err(_) = env::var("RUST_LOG") {
        env::set_var("RUST_LOG", "subscribe=DEBUG");
    }

    pretty_env_logger::init();

    let endpoint = match env::var("SINK_URL") {
        Ok(url) => {
            info!("Collecting at {}", url);
            url
        }
        Err(_) => {
            info!("SINK_URL not set, collecting at {}", DEFAULT_SINK_URL);
            DEFAULT_SINK_URL.to_owned()
        }
    };

    let ctx = Context::new();

    let mut socket = pull(&ctx).bind(&endpoint)?;

    while let Some(msgs) = socket.next().await {
        info!(
            "Pull: {:?}",
            msgs?
                .into_iter()
                .map(|msg| msg.try_into().expect("valid message"))
                .collect::<Vec<msg::ProducerMessage>>()
        );
    }

    Ok(())
}
