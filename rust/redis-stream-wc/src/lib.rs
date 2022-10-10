use bb8_redis::{bb8, RedisConnectionManager};

use redis::AsyncCommands;

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

pub const DEAULT_REDIS_URL: &str = "redis://localhost:6379/";
pub const DEAULT_STREAM_ID: &str = "counter";
pub const REDIS_MSG_KEY: &str = "msg";

#[derive(Debug, Serialize, Deserialize)]
pub enum Message {
    Count { client_id: String, data: String },

    Disconnect { client_id: String },

    Terminate,
}

impl TryFrom<Vec<u8>> for Message {
    type Error = String;

    #[inline(always)]
    fn try_from(value: Vec<u8>) -> Result<Self, Self::Error> {
        serde_json::from_slice(&value).map_err(|e| e.to_string())
    }
}

impl TryFrom<redis::Value> for Message {
    type Error = String;

    #[inline]
    fn try_from(value: redis::Value) -> Result<Self, Self::Error> {
        if let redis::Value::Data(bytes) = value {
            bytes.try_into()
        } else {
            Err(format!("Invalid Redis payload: {:?}", value))
        }
    }
}

impl TryFrom<HashMap<String, redis::Value>> for Message {
    type Error = String;

    #[inline]
    fn try_from(mut value: HashMap<String, redis::Value>) -> Result<Self, Self::Error> {
        if let Some(v) = value.remove(REDIS_MSG_KEY) {
            v.try_into()
        } else {
            Err(format!("No {} key in Redis Stream entry", REDIS_MSG_KEY))
        }
    }
}

pub async fn send(pool: &bb8::Pool<RedisConnectionManager>, receiver: String, msg: Message) {
    // Note: even better would be serializing directly into bytes
    let payload = serde_json::to_string(&msg).expect("message serialization");

    let pool = pool.clone();

    tokio::spawn(async move {
        let mut conn = pool.get().await.expect("Redis connection");
        let _: () = conn
            .xadd(receiver, "*", &[(REDIS_MSG_KEY, payload)])
            .await
            .expect("XADD: payload sent");
    })
    .await
    .expect("message sent");
}
