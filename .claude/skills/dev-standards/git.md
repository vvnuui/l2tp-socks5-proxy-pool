# Git 提交规范

## 1. 提交消息格式
遵循 Conventional Commits 规范:

```
<type>(<scope>): <subject>

<body>

<footer>
```

## 2. Type 类型
| 类型 | 描述 |
|------|------|
| feat | 新功能 |
| fix | 修复 Bug |
| docs | 文档更新 |
| style | 代码格式 (不影响功能) |
| refactor | 代码重构 |
| perf | 性能优化 |
| test | 测试相关 |
| build | 构建/依赖变更 |
| ci | CI/CD 配置 |
| chore | 其他杂项 |

## 3. Scope 范围
| 范围 | 描述 |
|------|------|
| backend | Django 后端 |
| frontend | Vue 前端 |
| network | 网络配置/脚本 |
| docker | Docker 相关 |
| api | API 接口 |
| model | 数据模型 |
| ui | 界面组件 |

## 4. 示例
```bash
# 新功能
feat(backend): add L2TP account management API

# 修复
fix(network): resolve routing table cleanup issue

# 文档
docs(readme): update installation instructions

# 重构
refactor(frontend): extract account list component

# 多行消息
feat(api): implement proxy start/stop endpoints

- Add POST /api/proxies/{id}/start/ endpoint
- Add POST /api/proxies/{id}/stop/ endpoint
- Add Celery task for async proxy management

Closes #123
```

## 5. 分支命名
| 类型 | 格式 | 示例 |
|------|------|------|
| 主分支 | main | main |
| 开发分支 | develop | develop |
| 功能分支 | feature/{desc} | feature/add-proxy-auth |
| 修复分支 | fix/{desc} | fix/routing-cleanup |
| 发布分支 | release/{version} | release/1.0.0 |
| 热修复 | hotfix/{desc} | hotfix/critical-bug |

## 6. 工作流程
```
1. 从 develop 创建功能分支
   git checkout -b feature/add-account-api develop

2. 开发并提交
   git add .
   git commit -m "feat(api): add account CRUD endpoints"

3. 推送并创建 PR
   git push origin feature/add-account-api

4. Code Review 后合并到 develop

5. 发布时从 develop 创建 release 分支
   git checkout -b release/1.0.0 develop

6. 测试通过后合并到 main 并打 tag
   git checkout main
   git merge release/1.0.0
   git tag -a v1.0.0 -m "Release 1.0.0"
```

## 7. PR 模板
```markdown
## 变更说明
<!-- 简述本次变更内容 -->

## 变更类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 性能优化 (perf)
- [ ] 测试 (test)
- [ ] 其他

## 影响范围
- [ ] 后端 API
- [ ] 前端界面
- [ ] 网络配置
- [ ] Docker/部署
- [ ] 数据库

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试通过
- [ ] 无需测试

## 检查清单
- [ ] 代码符合项目规范
- [ ] 已添加必要的注释
- [ ] 已更新相关文档
- [ ] 无安全漏洞

## 相关 Issue
<!-- 关联的 Issue 编号，如 Closes #123 -->

## 截图 (如适用)
<!-- 界面变更的截图 -->
```

## 8. Commit Hook (可选)
```bash
# .git/hooks/commit-msg
#!/bin/bash

commit_msg=$(cat "$1")
pattern="^(feat|fix|docs|style|refactor|perf|test|build|ci|chore)(\(.+\))?: .{1,72}$"

if ! echo "$commit_msg" | grep -qE "$pattern"; then
    echo "错误: 提交消息不符合规范"
    echo "格式: <type>(<scope>): <subject>"
    echo "示例: feat(api): add user authentication"
    exit 1
fi
```

## 9. 版本号规范
遵循语义化版本 (SemVer):
- **MAJOR**: 不兼容的 API 变更
- **MINOR**: 向后兼容的功能新增
- **PATCH**: 向后兼容的 Bug 修复

示例: `1.2.3`
- 1 = 主版本号
- 2 = 次版本号
- 3 = 修订号
