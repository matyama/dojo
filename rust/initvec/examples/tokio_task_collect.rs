use initvec::InitVec;
use tokio::task::JoinSet;

#[allow(dead_code)]
#[derive(Debug)]
struct Data {
    text: String,
    len: usize,
}

async fn process(i: usize, text: String) -> Result<(usize, Data), usize> {
    let len = text.len();
    let data = Data { text, len };
    Ok((i, data))
}

#[tokio::main]
async fn main() {
    let inputs = vec!["hello", "world"];
    let mut tasks = JoinSet::new();

    for (i, text) in inputs.iter().enumerate() {
        tasks.spawn(process(i, text.to_string()));
    }

    let mut results = InitVec::with_capacity(tasks.len());

    while let Some(result) = tasks.join_next().await {
        match result {
            Ok(Ok((i, data))) => results.insert(i, data),
            Ok(Err(i)) => eprintln!("task {i} failed"),
            Err(e) if e.is_panic() => std::panic::resume_unwind(e.into_panic()),
            Err(e) if e.is_cancelled() => eprintln!("task was cancelled: {e:?}"),
            other => unreachable!("failed to get task result: {other:?}"),
        }
    }

    match results.try_init() {
        Ok(results) => {
            println!("collected all data: {results:?}");

            let corpus = results
                .iter()
                .map(|data| data.text.as_str())
                .collect::<Vec<_>>();

            assert_eq!(inputs, corpus);
        }
        Err(results) => println!("collected partial data: {results:?}"),
    }
}
