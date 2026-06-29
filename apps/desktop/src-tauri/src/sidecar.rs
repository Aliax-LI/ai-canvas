use std::io::{Error, ErrorKind};
use std::net::TcpListener;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::time::{Duration, Instant};

use tauri::{AppHandle, Manager};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

enum SidecarProcess {
    Dev(Child),
    Prod(CommandChild),
}

impl SidecarProcess {
    fn kill(self) {
        match self {
            SidecarProcess::Dev(mut child) => {
                let _ = child.kill();
                let _ = child.wait();
            }
            SidecarProcess::Prod(child) => {
                let _ = child.kill();
            }
        }
    }
}

pub struct SidecarManager {
    pub port: u16,
    process: Mutex<Option<SidecarProcess>>,
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
        if let Ok(mut guard) = self.process.lock() {
            if let Some(process) = guard.take() {
                process.kill();
            }
        }
    }
}

pub fn start_sidecar(app: &AppHandle) -> Result<SidecarManager, Box<dyn std::error::Error>> {
    let data_dir = resolve_data_dir(app);
    std::fs::create_dir_all(&data_dir)?;

    let port = find_available_port()?;
    let process = spawn_sidecar(app, port, &data_dir)?;

    wait_for_health(port, Duration::from_secs(60))?;

    Ok(SidecarManager {
        port,
        process: Mutex::new(Some(process)),
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

fn sidecar_args(port: u16, data_dir: &str) -> [String; 6] {
    [
        "--host".into(),
        "127.0.0.1".into(),
        "--port".into(),
        port.to_string(),
        "--data-dir".into(),
        data_dir.into(),
    ]
}

fn spawn_sidecar(
    app: &AppHandle,
    port: u16,
    data_dir: &Path,
) -> Result<SidecarProcess, Box<dyn std::error::Error>> {
    let data_dir = data_dir
        .to_str()
        .ok_or("data directory path is not valid UTF-8")?;
    let args = sidecar_args(port, data_dir);

    if cfg!(debug_assertions) {
        return spawn_dev_sidecar(port, data_dir);
    }

    spawn_prod_sidecar(app, &args)
}

fn spawn_dev_sidecar(port: u16, data_dir: &str) -> Result<SidecarProcess, Box<dyn std::error::Error>> {
    let repo_root = find_repo_root()?;
    let args = sidecar_args(port, data_dir);

    let mut command = Command::new("uv");
    command
        .arg("run")
        .arg("infinite-canvas")
        .args(&args)
        .current_dir(&repo_root)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped());

    let mut child = command.spawn().map_err(|error| {
        format!(
            "failed to spawn `uv run infinite-canvas` in {}: {error}",
            repo_root.display()
        )
    })?;

    pipe_stdio_to_log(child.stdout.take(), child.stderr.take(), "dev");

    Ok(SidecarProcess::Dev(child))
}

fn spawn_prod_sidecar(
    app: &AppHandle,
    args: &[String],
) -> Result<SidecarProcess, Box<dyn std::error::Error>> {
    let (mut rx, child) = app
        .shell()
        .sidecar("infinite-canvas")?
        .args(args)
        .spawn()
        .map_err(|error| format!("failed to spawn bundled sidecar: {error}"))?;

    std::thread::spawn(move || {
        tauri::async_runtime::block_on(async move {
            while let Some(event) = rx.recv().await {
                match event {
                    CommandEvent::Stdout(line) => {
                        eprintln!("[sidecar] {}", String::from_utf8_lossy(&line));
                    }
                    CommandEvent::Stderr(line) => {
                        eprintln!("[sidecar:err] {}", String::from_utf8_lossy(&line));
                    }
                    CommandEvent::Error(error) => {
                        eprintln!("[sidecar] error: {error}");
                    }
                    CommandEvent::Terminated(payload) => {
                        eprintln!(
                            "[sidecar] terminated (code={:?}, signal={:?})",
                            payload.code, payload.signal
                        );
                        break;
                    }
                    _ => {}
                }
            }
        });
    });

    Ok(SidecarProcess::Prod(child))
}

fn pipe_stdio_to_log(
    stdout: Option<std::process::ChildStdout>,
    stderr: Option<std::process::ChildStderr>,
    label: &str,
) {
    if let Some(out) = stdout {
        let tag = label.to_string();
        std::thread::spawn(move || {
            use std::io::{BufRead, BufReader};
            let reader = BufReader::new(out);
            for line in reader.lines().map_while(Result::ok) {
                eprintln!("[sidecar:{tag}] {line}");
            }
        });
    }

    if let Some(err) = stderr {
        let tag = format!("{label}:err");
        std::thread::spawn(move || {
            use std::io::{BufRead, BufReader};
            let reader = BufReader::new(err);
            for line in reader.lines().map_while(Result::ok) {
                eprintln!("[sidecar:{tag}] {line}");
            }
        });
    }
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

fn resolve_data_dir(app: &AppHandle) -> PathBuf {
    if cfg!(debug_assertions) {
        if let Ok(repo_root) = find_repo_root() {
            return repo_root.join(".infinite-canvas-dev");
        }
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
        .unwrap_or_else(|| PathBuf::from(".infinite-canvas-dev"))
}
