use std::io::{Error, ErrorKind};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager};

pub struct SidecarManager {
    pub port: u16,
    child: Mutex<Option<Child>>,
}

impl SidecarManager {
    pub fn api_base(&self) -> String {
        format!("http://127.0.0.1:{}/api", self.port)
    }

    pub fn server_origin(&self) -> String {
        format!("http://127.0.0.1:{}", self.port)
    }

    pub fn initialization_script(&self) -> String {
        format!(
            "window.__INFINITE_CANVAS_API__='{}';window.__INFINITE_CANVAS_ORIGIN__='{}';",
            self.api_base(),
            self.server_origin()
        )
    }

    pub fn kill(&self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
                let _ = child.wait();
            }
        }
    }
}

pub fn start_sidecar(app: &AppHandle) -> Result<SidecarManager, Box<dyn std::error::Error>> {
    let repo_root = find_repo_root()?;
    let data_dir = resolve_data_dir(app, &repo_root);
    std::fs::create_dir_all(&data_dir)?;

    let port = find_available_port()?;
    let child = spawn_sidecar_process(port, &data_dir, &repo_root)?;

    wait_for_health(port, Duration::from_secs(60))?;

    Ok(SidecarManager {
        port,
        child: Mutex::new(Some(child)),
    })
}

fn find_available_port() -> Result<u16, Error> {
    for port in 3000u16..4000 {
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return Ok(port);
        }
    }
    Err(Error::new(
        ErrorKind::AddrInUse,
        "no available port in range 3000-3999",
    ))
}

fn wait_for_health(port: u16, timeout: Duration) -> Result<(), Box<dyn std::error::Error>> {
    let url = format!("http://127.0.0.1:{}/api/app-info", port);
    let start = Instant::now();

    while start.elapsed() < timeout {
        if let Ok(response) = reqwest::blocking::get(&url) {
            if response.status().is_success() {
                return Ok(());
            }
        }
        std::thread::sleep(Duration::from_millis(400));
    }

    Err(format!(
        "sidecar health check timed out after {}s (GET {url})",
        timeout.as_secs()
    )
    .into())
}

fn spawn_sidecar_process(
    port: u16,
    data_dir: &Path,
    repo_root: &Path,
) -> Result<Child, Box<dyn std::error::Error>> {
    let data_dir = data_dir
        .to_str()
        .ok_or("data directory path is not valid UTF-8")?;

    let child = Command::new("uv")
        .args([
            "run",
            "infinite-canvas",
            "--host",
            "127.0.0.1",
            "--port",
            &port.to_string(),
            "--data-dir",
            data_dir,
        ])
        .current_dir(repo_root)
        .stdout(Stdio::null())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|error| {
            format!(
                "failed to spawn `uv run infinite-canvas` in {}: {error}",
                repo_root.display()
            )
        })?;

    Ok(child)
}

fn find_repo_root() -> Result<PathBuf, Error> {
    let mut dir = std::env::current_dir()?;

    loop {
        let manifest = dir.join("pyproject.toml");
        if manifest.is_file() {
            let content = std::fs::read_to_string(&manifest)?;
            if content.contains("name = \"infinite-canvas\"") {
                return Ok(dir);
            }
        }

        if !dir.pop() {
            break;
        }
    }

    Err(Error::new(
        ErrorKind::NotFound,
        "could not locate monorepo root (pyproject.toml with infinite-canvas)",
    ))
}

fn resolve_data_dir(app: &AppHandle, repo_root: &Path) -> PathBuf {
    if cfg!(debug_assertions) {
        return repo_root.join(".infinite-canvas-dev");
    }

    #[cfg(target_os = "macos")]
    {
        if let Some(home) = dirs::home_dir() {
            return home.join("Library/Application Support/infinite-canvas");
        }
    }

    #[cfg(target_os = "windows")]
    {
        if let Some(data) = dirs::data_dir() {
            return data.join("infinite-canvas");
        }
    }

    if let Ok(dir) = app.path().app_data_dir() {
        return dir;
    }

    dirs::home_dir()
        .map(|home| home.join(".infinite-canvas"))
        .unwrap_or_else(|| repo_root.join(".infinite-canvas-dev"))
}
