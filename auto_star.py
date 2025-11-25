#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Star Bot
- 从环境变量 USER_TOKEN 读取 Personal Access Token (PAT)
- 从环境变量 TARGET_USERS 或文件 targets.txt 读取要关注的 GitHub 用户列表
- 每个用户只检查最近 N 个仓库（默认 10），若未 Star 则执行 Star 并判断是否为第一个 Star
"""

import os
import sys
import logging
from github import Github, GithubException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

TOKEN = os.getenv("USER_TOKEN")
if not TOKEN:
    logging.error("未找到 USER_TOKEN（Personal Access Token）。请在 GitHub Secrets 中添加 USER_TOKEN。")
    sys.exit(1)

# 获取目标用户列表：优先从环境变量 TARGET_USERS（逗号分隔），否则读取 targets.txt（每行一个）
def load_target_users():
    env = os.getenv("TARGET_USERS", "").strip()
    if env:
        return [u.strip() for u in env.split(",") if u.strip()]
    # 尝试读取 targets.txt
    try:
        with open("targets.txt", "r", encoding="utf-8") as f:
            users = []
            for line in f:
                line = line.split("#", 1)[0].strip()  # 支持注释
                if line:
                    users.append(line)
            return users
    except FileNotFoundError:
        logging.error("未提供目标用户列表。请在环境变量 TARGET_USERS 中设置或在仓库根目录放置 targets.txt。")
        sys.exit(1)

# 每个用户检查的仓库数量上限（默认 10）
CHECK_LIMIT = int(os.getenv("CHECK_LIMIT", "10"))

def main():
    g = Github(TOKEN, per_page=100)
    try:
        me = g.get_user()
        logging.info(f"当前登录用户: {me.login}")
    except GithubException as e:
        logging.error(f"使用 TOKEN 登录 GitHub 失败: {e}")
        sys.exit(1)

    targets = load_target_users()
    if not targets:
        logging.error("目标用户列表为空，退出。")
        sys.exit(1)

    for target_username in targets:
        logging.info("------ 正在检查程序员: %s ------", target_username)
        try:
            target_user = g.get_user(target_username)
            repos = target_user.get_repos(sort="created", direction="desc")

            for i, repo in enumerate(repos):
                if i >= CHECK_LIMIT:
                    break

                try:
                    if me.has_in_starred(repo):
                        logging.debug("[已关注] %s (跳过)", repo.full_name)
                        continue

                    logging.info("发现未关注项目: %s", repo.full_name)
                    current_stars = repo.stargazers_count

                    # 点 Star
                    me.add_to_starred(repo)
                    logging.info("--> 已执行 Star 操作: %s", repo.full_name)

                    if current_stars == 0:
                        logging.info("🎉 恭喜！你是 %s 的第一个 Star 用户！", repo.full_name)
                    else:
                        logging.info("已补票。之前 Star 数: %d，当前可能为: %d", current_stars, current_stars + 1)

                except GithubException as e:
                    logging.warning("对仓库 %s 操作失败: %s", getattr(repo, "full_name", "(unknown)"), e)
                except Exception as e:
                    logging.warning("处理仓库 %s 时发生异常: %s", getattr(repo, "full_name", "(unknown)"), e)

        except GithubException as e:
            logging.error("检查用户 %s 时发生 GitHub 错误: %s", target_username, e)
        except Exception as e:
            logging.error("检查用户 %s 时发生未知错误: %s", target_username, e)

    # 输出剩余速率信息（可选）
    try:
        rate = g.get_rate_limit().core
        logging.info("API 速率限额: 剩余 %d / %d, reset at %s", rate.remaining, rate.limit, rate.reset)
    except Exception:
        pass

if __name__ == "__main__":
    main()
