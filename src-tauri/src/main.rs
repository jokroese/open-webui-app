use log::{error, info};
use reqwest::blocking::get;
use std::path::Path;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use std::{env, thread};
use tauri_plugin_log::Builder as LogBuilder;

fn start_backend() -> std::process::Child {
    let backend_path = env::current_dir()
        .expect("Failed to get current directory")
        .join("../backend/start.sh");

    let max_retries = 3;
    for attempt in 1..=max_retries {
        println!("Starting backend (Attempt {}/{})...", attempt, max_retries);

        let process = Command::new("bash")
            .arg(backend_path.to_str().expect("Failed to convert path"))
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn();

        if let Ok(child) = process {
            return child;
        }

        eprintln!("Backend failed to start. Retrying...");
        thread::sleep(Duration::from_secs(5));
    }

    eprintln!("❌ Backend failed after {} attempts.", max_retries);
    std::process::exit(1);
}

fn check_backend_health() -> bool {
    let health_url = "http://localhost:8080/health";
    let max_wait_time = Duration::from_secs(60);
    let start_time = Instant::now();

    println!("⌛ Waiting for backend to start...");

    while start_time.elapsed() < max_wait_time {
        match get(health_url) {
            Ok(response) if response.status().is_success() => {
                println!("✅ Backend is ready!");
                return true;
            }
            Err(err) => println!("🔴 Health check error: {}", err),
            _ => {}
        }

        thread::sleep(Duration::from_secs(1));
    }

    eprintln!("❌ Backend startup timed out.");
    false
}

fn start_ollama_loop(ollama_path: String) {
    thread::spawn(move || loop {
        println!("Starting Ollama...");

        let mut ollama_process = Command::new(&ollama_path)
            .arg("serve")
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn()
            .expect("Failed to start Ollama");

        if let Ok(status) = ollama_process.wait() {
            println!("Ollama exited with status: {:?}", status);
            thread::sleep(Duration::from_secs(3));
        } else {
            println!("❌ Failed to wait for Ollama process.");
            break;
        }
    });
}

fn detect_ollama() -> Option<String> {
    if let Ok(output) = Command::new("ollama").arg("--version").output() {
        if output.status.success() {
            return Some("ollama".to_string());
        }
    }

    let bundled_path = env::current_dir()
        .expect("Failed to get current directory")
        .join("ollama/ollama");
    if Path::new(&bundled_path).exists() {
        return Some(
            bundled_path
                .to_str()
                .expect("Failed to convert path to string")
                .to_string(),
        );
    }

    None
}

fn main() {
    tauri::Builder::default()
        .plugin(LogBuilder::default().build())
        .setup(|_app| {
            info!("🚀 App is starting...");

            let mut backend = start_backend();
            if !check_backend_health() {
                error!("Backend failed.");
                backend.kill().expect("Failed to kill backend");
                std::process::exit(1);
            }

            match detect_ollama() {
                Some(ollama_path) => {
                    info!("Using Ollama at: {}", ollama_path);
                    start_ollama_loop(ollama_path);
                }
                None => {
                    error!("Ollama not found.");
                    std::process::exit(1);
                }
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running Tauri application")
        .run(|_app_handle, _event| {});
}
