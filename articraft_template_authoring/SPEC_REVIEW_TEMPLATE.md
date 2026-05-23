# Spec Review Template

用于人工审核 agent 写出的 `specs/<category_slug>.md`。

## Review Target

| 项 | 值 |
|---|---|
| category_slug | <category_slug> |
| spec path | articraft_template_authoring/specs/<category_slug>.md |
| reviewer status | pending / approved / rejected |

## 必查项

- [ ] agent 是否声明已枚举并完整读取该类别全部 5 星样本的 `model.py / revision.json / record.json`。
- [ ] spec 是否只保留被采纳为模板依据的 `model.py:Lx-Ly` 来源索引，没有把已读但未采用的样本索引塞进来。
- [ ] Parts / Joints / 关键参数的来源索引是否来自适合模板复用的 5 星样本代码片段。
- [ ] 核心身份是否清楚，能否区分相邻类别。
- [ ] required parts 是否过多，是否混入了单样本特有装饰。
- [ ] optional parts 是否合理。
- [ ] 关节 type / axis / origin / range 是否明确。
- [ ] 参数是否能产生结构级变化，而不是只换色。
- [ ] `已有模板写法参考` 是否只用于定位已有 11 个模板的骨架、SDK 写法和测试风格，而不是决定或替代被采纳的 5 星样本源码片段。
- [ ] Validator 是否能转成测试。
- [ ] Reject cases 是否覆盖关键失败模式。

## 审核结论

```text
approved / rejected
```

## 修改意见

```text
...
```

## Template 阶段提醒

审核通过后，agent 写模板时应优先改编 spec 中已采纳并带 `model.py:Lx-Ly` 索引的 5 星样本部件 / 关节 / 参数代码。已有 11 个旧模板只用于统一代码结构、SDK 用法、palette、validator 和测试风格。
