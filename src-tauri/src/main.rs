use reqwest::blocking::get;
use std::process::{Command, Stdio};
use std::time::Duration;
use std::{env, thread};

fn start_backend() -> std::process::Child {
    let backend_path = env::current_dir()
        .expect("Failed to get current directory")
        .join("backend/start.sh");

    Command::new("bash")
        .arg(
            backend_path
                .to_str()
                .expect("Failed to convert path to string"),
        )
        .stdout(Stdio::inherit())
        .stderr(Stdio::inherit())
        .spawn()
        .expect("Failed to start backend")
}

fn check_backend_health() -> bool {
    let health_url = "http://localhost:8080/health";
    for _ in 0..10 {
        if let Ok(response) = get(health_url) {
            if response.status().is_success() {
                return true;
            }
        }
        thread::sleep(Duration::from_secs(1));
    }
    false
}

fn main() {
    tauri::Builder::default()
        .setup(|_app| {
            let mut backend = start_backend();

            // Ensure backend is running
            if !check_backend_health() {
                eprintln!("Backend failed to start or is unhealthy.");
                backend.kill().expect("Failed to kill backend process");
                std::process::exit(1);
            }

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|_app_handle, _event| {});
}
