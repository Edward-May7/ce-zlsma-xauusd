# GitHub Publish Guide / GitHub 发布指南

The local project is ready for open-source publishing. Publishing is blocked only by local GitHub tooling or remote repository access.

本地项目已经准备好开源发布；当前只缺本机 GitHub 工具或远端仓库访问权限。

## Recommended Path / 推荐路径

1. Install Git and GitHub CLI.
2. Authenticate with `gh auth login`.
3. Create a public repository named `ce-zlsma-xauusd`.
4. Run the commands below from this folder.

1. 安装 Git 和 GitHub CLI。
2. 执行 `gh auth login` 完成认证。
3. 创建名为 `ce-zlsma-xauusd` 的公开仓库。
4. 在本目录运行下面命令。

```powershell
git init
git branch -M main
git add .
git commit -m "Open-source CE ZLSMA XAUUSD strategy"
gh repo create ce-zlsma-xauusd --public --source . --remote origin --push
```

If the repository already exists:

如果远端仓库已经存在：

```powershell
git init
git branch -M main
git add .
git commit -m "Open-source CE ZLSMA XAUUSD strategy"
git remote add origin https://github.com/Edward-May7/ce-zlsma-xauusd.git
git push -u origin main
```

## Current Blockers / 当前阻塞

- `git` is not available in PATH.
- `gh` is not available in PATH.
- The connected GitHub App can identify user `Edward-May7`, but it has no installed repositories or account installations available to this session.

- 当前 PATH 中没有 `git`。
- 当前 PATH 中没有 `gh`。
- 已连接的 GitHub App 可以识别用户 `Edward-May7`，但本会话没有可访问的已安装仓库或账号安装权限。
