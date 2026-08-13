// 直触深网 —— 预加载脚本（渲染进程）
// 作为主进程与渲染页面之间的安全桥接。当前前端页面通过同源 fetch 与后端通信，
// 此处仅暴露最小化的只读信息，不开放 Node 能力给页面。
// 【直触深网】版权所有：洪声越Jeff 联系邮箱：HongshengyueJeff@163.com
window.__CYBER__ = {
  platform: process.platform,
  version: "1.0.0",
};
