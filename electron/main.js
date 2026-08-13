// 直触深网 —— Electron 主进程
// 职责：拉起内嵌的 Python 后端（CyberSecBackend.exe），等待其就绪后，
// 在渲染进程中加载本地 Web 页面（http://127.0.0.1:8029）。
// 【直触深网】版权所有：洪声越Jeff 联系邮箱：HongshengyueJeff@163.com
const { app, BrowserWindow } = require("electron");
const { spawn } = require("child_process");
const http = require("http");
const path = require("path");
const fs = require("fs");

const PORT_DEFAULT = 8029;
const IS_WIN = process.platform === "win32";

// 单实例锁，避免重复启动多个后端
if (!app.requestSingleInstanceLock()) {
  app.quit();
  return;
}

// 解析内嵌后端可执行文件位置
function resolveBackend() {
  const name = IS_WIN ? "CyberSecBackend.exe" : "CyberSecBackend";
  let p = path.join(process.resourcesPath, "resources", "backend", name);
  if (!fs.existsSync(p)) p = path.join(__dirname, "resources", "backend", name);
  return p;
}

function resolveIcon() {
  let p = path.join(process.resourcesPath, "resources", "build", "icon.ico");
  if (!fs.existsSync(p)) p = path.join(__dirname, "build", "icon.ico");
  return fs.existsSync(p) ? p : undefined;
}

// 探活：直到后端返回 200 或超时
function waitForServer(port, timeoutMs) {
  return new Promise((resolve, reject) => {
    const start = Date.now();
    const tryOnce = () => {
      const req = http.get(
        { host: "127.0.0.1", port, path: "/", timeout: 1500 },
        (res) => {
          res.resume();
          resolve(port);
        }
      );
      req.on("error", () => {
        if (Date.now() - start > timeoutMs) reject(new Error("后端启动超时"));
        else setTimeout(tryOnce, 800);
      });
      req.on("timeout", () => req.destroy());
    };
    tryOnce();
  });
}

let backendChild = null;
let backendPort = PORT_DEFAULT;

function startBackend() {
  const exe = resolveBackend();
  if (!fs.existsSync(exe)) {
    return Promise.reject(new Error("未找到后端程序：" + exe));
  }
  return new Promise((resolve, reject) => {
    backendChild = spawn(
      exe,
      ["--no-browser", "--port", String(PORT_DEFAULT)],
      { windowsHide: true, stdio: ["ignore", "pipe", "pipe"] }
    );
    backendChild.stdout.on("data", (d) => {
      const m = String(d).match(/127\.0\.0\.1:(\d+)/);
      if (m) backendPort = parseInt(m[1], 10);
    });
    backendChild.stderr.on("data", (d) => console.error("[backend]", String(d)));
    backendChild.on("error", (e) => reject(e));
    // 给后端一点启动时间后开始探活
    setTimeout(() => {
      waitForServer(backendPort, 30000).then(resolve).catch(reject);
    }, 1500);
  });
}

function createWindow() {
  const opts = {
    width: 1280,
    height: 860,
    backgroundColor: "#f5f7fa",
    show: false,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  };
  const icon = resolveIcon();
  if (icon) opts.icon = icon;
  const win = new BrowserWindow(opts);
  win.loadURL(`http://127.0.0.1:${backendPort}/`);
  win.once("ready-to-show", () => win.show());
  return win;
}

function killBackend() {
  if (backendChild) {
    try {
      backendChild.kill("SIGTERM");
    } catch (e) {
      /* ignore */
    }
    backendChild = null;
  }
}

app.whenReady().then(async () => {
  try {
    await startBackend();
  } catch (e) {
    console.error(e);
  }
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  killBackend();
  if (process.platform !== "darwin") app.quit();
});
app.on("before-quit", killBackend);
