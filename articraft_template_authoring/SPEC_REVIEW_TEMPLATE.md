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
- [ ] 是否包含 `部件多样性审计（Part Diversity Audit）`。
- [ ] 审计是否覆盖所有核心部件类型，而不是只检查整机有没有 enum。
- [ ] 若某部件存在连续尺寸无法表达的定性差异，是否补了 `*_shape / *_style / *_profile / *_variant / *_layout`。
- [ ] 若某部件没有观察到多样性，是否记录 `observed_variation = none`；若只有尺寸/角度变化，是否说明连续参数足够。
- [ ] `已有模板写法参考` 是否只用于定位旧 11 个 gold-standard 模板的骨架、SDK 写法、测试风格，以及新 20+ 模板的二级经验，而不是决定或替代被采纳的 5 星样本源码片段。
- [ ] 若 spec 覆盖多个不兼容主运动 spine，是否已标注建议拆分 slug 或明确模板阶段只实现的稳定子域。
- [ ] spec 中被采纳的 5 星样本片段是否足够支持后续模板 helper / part / joint 的实际源码改编，而不是只作为阅读引用。
- [ ] 参数表是否支持拓扑匹配的约束派生：先确定外壳 / frame / base / rail / hinge line / axis / socket / contact plane / symmetry plane 等主约束基准，再派生数量、尺寸、origin、orientation、joint range；没有把抽屉柜公式机械套到其他拓扑。
- [ ] 关节表是否体现真实部件语义：父件、子件、closed pose、运动方向、axis、origin、range 都明确。
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

审核通过后，agent 写模板时应优先改编 spec 中已采纳并带 `model.py:Lx-Ly` 索引的 5 星样本部件 / 关节 / 参数代码。模板文件至少 1000 行，且 1000 是下限不是上限。旧 11 个 gold-standard 模板用于统一代码结构、SDK 用法、palette、validator 和测试风格；新 20+ 模板可作为拆分、seed domain、QC/预览修复和测试断言的二级参考；`MATURE_TEMPLATE_METHOD.md` 用于决定拆分/收窄、参数化、拓扑匹配的空间约束、joint 语义、seed domain、`resolve_config`、QC 和自动调参闭环。抽屉柜 envelope-first 只是一个约束例子，不是通用公式。多类别模板实现必须逐个或最多 2-3 个同族模板一组推进；测试、QC、预览和明显调参问题必须由 agent 自己闭环解决。
