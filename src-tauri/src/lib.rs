#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    use log::{error, info};
    use tauri::{Manager, RunEvent};
    use tauri_plugin_log::Builder as LogBuilder;

    info!("🚀 Starting Open WebUI...");

    let app = tauri::Builder::default()
        // structured logging
        .plugin(LogBuilder::default().level(log::LevelFilter::Debug).build())
        .setup(|app| {
            info!("🔄 Running setup phase...");

            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building Tauri application");

    app.run(move |_app_handle, event| match event {
        RunEvent::Reopen { .. } => {
            info!("🔄 App reopened!");
        }
        RunEvent::ExitRequested { api, .. } => {
            info!("🛑 Exit requested. Cleaning up...");
            api.prevent_exit();
        }
        _ => {}
    });
}
