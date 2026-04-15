# Pokemon Champions Assistant — Project Rules

## 项目概览
- 仓库：`LuckyDogzyc/pokemon-champions-assistant`
- 当前状态：初始化阶段，目前仓库只有 `LICENSE` 和已安装的 `.claude/` 工作流模板。
- 开发模式：默认采用 `vibe-coding-zh-kit` 顺序：`prime -> create-rules -> create-prd(可选) -> plan-feature -> execute -> commit`

## 技术栈
- 当前尚未确定最终技术栈。
- 在技术栈未确认前，不要直接铺开工程脚手架；先明确产品目标、运行平台、数据来源、部署方式。

## 目录结构
- `.claude/commands/`：中文工作流命令模板
- `.claude/skills/`：辅助技能模板
- `.agents/plans/`：功能计划输出目录
- `CLAUDE.md`：本项目规则

## 当前阶段协作规则
1. 先定义产品目标和 MVP，再选技术方案。
2. 当前已确认 MVP 需要包含采集卡实时输入、双方当前场上宝可梦名称识别、资料查询、属性克制查询和人工修正能力。
3. 当前中文为第一优先识别语言，多语言映射需从架构上预留。
4. 在没有明确计划文件前，不直接实现大段业务代码。
5. 每个功能先产出计划文件到 `.agents/plans/`，再执行开发。
6. 所有实现都必须附带验证方式（至少包含运行/测试/手工验证之一）。
7. 提交采用原子提交，提交信息使用 `feat` / `fix` / `docs` / `refactor` 等前缀。

## 规划规则
在编写计划前，必须尽量明确：
- 目标用户是谁
- 要解决什么问题
- MVP 包含什么、不包含什么
- 运行平台（Web / Desktop / CLI / Bot / Mobile）
- 是否接入外部 API、数据库、认证、实时服务
- 验收标准是什么

## 常用 Git 命令
```bash
git status --short --branch
git log --oneline -10
git diff --stat
```

## 当前事实
- 默认分支：`main`
- 当前仓库无业务代码
- `.claude/` 已安装，可直接进入 PRD / 规划阶段

## 下一步建议
1. 先补充本项目的产品定义与 MVP 范围
2. 生成 `PRD.md`
3. 基于 PRD 输出 `.agents/plans/*.md` 实施计划
