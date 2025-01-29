use reqwest::blocking::get;
use std::path::Path;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};
use std::{env, thread};

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

    print!("Waiting for backend to start... ");

    while start_time.elapsed() < max_wait_time {
        if let Ok(response) = get(health_url) {
            if response.status().is_success() {
                println!("✅ Backend is ready!");
                return true;
            }
        }
        print!(".");
        std::io::Write::flush(&mut std::io::stdout()).unwrap();
        thread::sleep(Duration::from_secs(1));
    }

    eprintln!("\n❌ Backend took too long to start. Check logs for issues.");
    false
}

fn start_ollama(ollama_path: &str) -> std::process::Child {
    let max_retries = 3;
    for attempt in 1..=max_retries {
        println!("Starting Ollama (Attempt {}/{})...", attempt, max_retries);

        let process = Command::new(ollama_path)
            .arg("serve")
            .stdout(Stdio::inherit())
            .stderr(Stdio::inherit())
            .spawn();

        if let Ok(child) = process {
            return child;
        }

        eprintln!("Ollama failed to start. Retrying...");
        thread::sleep(Duration::from_secs(5));
    }

    eprintln!("❌ Ollama failed after {} attempts.", max_retries);
    std::process::exit(1);
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
        .setup(|_app| {
            let mut backend = start_backend();

            if !check_backend_health() {
                eprintln!("Backend failed to start or is unhealthy.");
                backend.kill().expect("Failed to kill backend process");
                std::process::exit(1);
            }

            match detect_ollama() {
                Some(ollama_path) => {
                    println!("Using Ollama at: {}", ollama_path);
                    let mut ollama_process = start_ollama(&ollama_path);

                    ctrlc::set_handler(move || {
                        if let Err(e) = ollama_process.kill() {
                            eprintln!("Failed to kill Ollama process: {}", e);
                        }
                        std::process::exit(0);
                    })
                    .expect("Error setting Ctrl-C handler");
                }
                None => {
                    eprintln!(
                        "Ollama not found. Please install it or include it in the bundled package."
                    );
                    std::process::exit(1);
                }
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running Tauri application")
        .run(|_app_handle, _event| {});
}
