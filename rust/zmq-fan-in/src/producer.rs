use std::time::Duration;

use futures::SinkExt;
use prost::bytes;
use prost::Message;
use tokio::time::sleep;

use log::info;

use std::env;
use tmq::{push, Context};

const DEFAULT_SINK_URL: &str = "tcp://127.0.0.1:6000";

pub mod msg {
    include!(concat!(env!("OUT_DIR"), "/msg.rs"));
}

impl TryFrom<msg::ProducerMessage> for Vec<u8> {
    type Error = prost::EncodeError;

    fn try_from(msg: msg::ProducerMessage) -> Result<Self, prost::EncodeError> {
        let mut buf = bytes::BytesMut::with_capacity(msg.encoded_len());
        msg.encode(&mut buf)?;
        Ok(buf.to_vec())
    }
}

#[tokio::main]
async fn main() -> tmq::Result<()> {
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
        let mut message = msg::ProducerMessage::default();
        message.sender = producer_id.clone();
        message.data = format!("{} := {}", &producer_id, i);

        i += 1;

        info!("Push: {:?}", &message);

        let multipart = vec![Vec::try_from(message).expect("message encoded")];
        socket.send(multipart).await?;
        sleep(Duration::from_millis(1000)).await;
    }
}
