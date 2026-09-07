# 本地使用与命令参考

以下命令均从项目目录运行。检索、准备输入、定位对象及局部编辑入口已做实际测试。输出目录和文件请选择新的版本名。

### 检索与准备生图输入

从论文整理完设计后，可以不依赖旧演示组件：

```sh
python3 scripts/afw.py priors --brief examples/design-brief.json --design examples/design-plan.json --layout stacked --output-dir .local/runs/design-stacked-v1
```

这个原创教学示例不含私人论文或素材。真实方法图应替换为从当前论文整理的说明和设计，不能照搬示例机制。加入参考图片时，为每张图填写借用职责；字段和双布局例子见 [设计方案格式](../references/design-plan.md)。

优先使用登记素材，不必选择旧组件：

```sh
python3 scripts/reference_registry.py register --id my-reference-v1 --path .local/references/my-reference.png --private --license unknown --status user-approved --approval-evidence '用户实际选择这张图的原话'
python3 scripts/afw.py search flow --include-private
python3 scripts/afw.py priors --brief .local/brief.json --reference-id my-reference-v1 --allow-private --output-dir .local/runs/my-figure/priors
```

多个 `--reference-id` 按顺序使用，第一张为主参考。已实际查看的新候选可以显式使用 `--allow-candidate-references`，但仍保留“候选”身份；已拒绝素材不会进入输入。不要为通过检查而编造用户认可。

`priors` 生成 `prompt.txt`、`image-tool-input.json` 和 `manifest.json`，不会自行调用模型。检查其中每张参考图后，再使用图像工具支持的真实图片附件方式；仅在提示词里写文件名不算传入参考图。

旧版三种字体的 ODE 组件已退出展示和参考选择。历史文件仅用于已有记录的复查，不作为新的绘图先验；需要空间表达时，参考当前的二维分布、三维网格及完整框架示例。

### 索引私人素材

```sh
python3 scripts/index_library.py --input /absolute/path/library.pptx --output-dir .local/library
```

索引和提取素材仅保存在 `.local/`，不修改原 PPTX。提取出的位图不是原生可编辑机制组件。索引不包含自动机制理解、母版继承元素重建或整页视觉分析。

默认私人检索读取 `.local/library/catalog.json`。原素材许可未知，不得直接公开或当作原创资产；上传到生图服务也应先确认授权。为生图输入显式选择私人图片时，需要同时使用 `--private-asset <索引中的资产ID>` 和 `--allow-private-references`，且输出仍须位于 `.local/`。

### 选中一个对象进行修改

完整绘图会话可根据真实对象名称自动准备选区请求并保留修改记录，见 [完整示例](../references/workflow-session.md#selected-region-feedback)。下面是独立编辑器的低层入口：

```sh
python3 scripts/afw.py inspect-pptx --pptx output/showcase/spatial-flow.pptx --slide 2
python3 scripts/selection_edit.py --scene examples/showcase/manifold.scene.json --request examples/showcase/move-label.json --output .local/manifold-edited-v1.json
python3 scripts/build_components.py --scene .local/manifold-edited-v1.json --output .local/manifold-edited-v1.svg
```

示例请求只将 `surface-target-label` 下移 8 px。编辑器保留源文件，生成新场景和 `.audit.json`；已有输出会被拒绝。实际使用建议加入源文件的 `expected_sha256`，避免对过期版本执行批注。

对象名称需要先核对，不能把应用批注编号直接当成 PPTX 文件编号。截图选区仍需人工或模型识别到准确对象。文字修改会标记需要科学复核；改变科学语义颜色必须明确允许。

### 导出可编辑 PPTX

读取当前环境的 presentations 技能后，在依赖齐全的环境运行：

```sh
node scripts/export_components.mjs --scene .local/manifold-edited-v1.json --output .local/exports/manifold-edited-v1.pptx --build-dir .local/build
```

重复 `--scene` 可把相同画布尺寸的多张图放进同一个 PPT。输出包括对象名称映射和预览；验证记录位于私人构建目录。对象映射同时记录场景与最终 PPT 的文件指纹。导出器会拒绝覆盖现有成品与副产物。

输出和构建目录分别保存。独立试用时显式指定同一试用目录下的 `output/` 与 `build/`，避免把临时检查文件混进交付目录。

基础演示目录仅在明确选择 `--rebuild-catalog` 时生成，且不覆盖已有文件。日常修改使用 `--scene`；不要把旧演示生成器用于替换已经确认或手工修改的图。

## 环境与依赖

Python 辅助脚本使用标准库，建议 Python 3.10 或更新版本。PPTX 导出依赖 Node.js、`@oai/artifact-tool` 以及 Codex presentations 技能中的检查与导出支持；这些依赖不是本项目自动安装的公共应用运行时。

导出脚本会尝试当前环境的模块，再使用 Codex 本机缓存路径。其他环境需要明确提供：

| 变量 | 内容 |
|---|---|
| `RUNTIME_NODE_MODULES` | 包含 `@oai/artifact-tool` 的 `node_modules` 目录 |
| `RUNTIME_NODE` | 相应 Node.js 可执行文件 |
| `RUNTIME_PYTHON` | presentations 检查脚本使用的 Python |
| `PRESENTATIONS_SKILL_DIR` | 包含 `container_tools/` 的 presentations 技能目录 |

字体还需要在目标环境中可用。不能仅凭本机成功就承诺其他电脑上的字体和排版一致；也不能只看场景文件便声称 PPTX 已完成视觉检查。

## 验证与边界

```sh
python3 -m unittest discover -s tests -v
```

自动测试覆盖参考输入准备、PPTX 对象定位、选择保护、无覆盖写入、来源指纹、私人素材限制、会话恢复及异常输入。修改后的版本需要重新检查，不会自动继承原版的用户认可。依赖当前环境的检查可能被跳过，应以实际测试输出为准。

测试**不证明所有论文机制正确，也不代表用户已认可图形美观程度**。实际交付仍需检查科学含义、最终尺寸和导出的 PPTX，并对局部修改前后未选区域进行比较。私人案例与试用报告不包含在公开仓库中。

目前不支持任意手工修改后的 PPTX 自动双向同步，不监听 PowerPoint 选区，也不自动理解截图范围。箭头尖可以作为独立原生形状编辑，但不应声称在 PowerPoint 中拖动任意模块时所有连线都会自动跟随。

来源与公开限制见 [provenance.md](../references/provenance.md)。私人素材、用户论文和本地记录不得随项目发布；发布工作流不等于获准发布使用它制作的私人案例。社交平台展示需要另行授权。
