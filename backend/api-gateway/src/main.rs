use axum::{
    routing::get,
    Router,
    response::Json,
    http::StatusCode,
};
use serde_json::{json, Value};
use std::net::SocketAddr;

#[tokio::main]
async fn main() {
    // build our application with a single route
    let app = Router::new()
        .route("/", get(root_handler));

    // bind to 0.0.0.0:8080 so it's reachable from docker, WSL, etc.
    let addr = SocketAddr::from(([0, 0, 0, 0], 8080));
    println!("🚀 Listening on http://{}", addr);

    // run it
    axum::Server::bind(&addr)
        .serve(app.into_make_service())
        .await
        .unwrap();
}

// a simple handler that returns JSON
async fn root_handler() -> (StatusCode, Json<Value>) {
    let body = json!({
        "message": "Hello, Hissabi!"
    });
    (StatusCode::OK, Json(body))
}
