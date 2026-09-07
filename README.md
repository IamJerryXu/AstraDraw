# Astra Figure Workflow

从**已有论文与方法**出发，使用素材库提供视觉参考，制作可编辑科研图，并按选中对象进行局部修改。论文决定科学含义；参考图帮助选择构图、字体、配色和表达方式，不替论文补充机制。

这是面向 Astra 在 Codex 中使用的绘图工作流与本地辅助脚本。核心是把论文里的机制变成读者能看懂的视觉关系，并让参考选择、构图判断和局部修改彼此衔接。项目以工作流、脚本和示例的形式提供，不是独立应用。

## 绘图的核心

**论文 → 视觉主线 → 素材先验与构图选择 → 生图探索 → 科学复核与可编辑重建 → 局部批注 → 最终尺寸检查。** 已有可编辑图的小改动直接进入局部修改。

| 环节 | 需要做出的判断 | 留下什么 |
| --- | --- | --- |
| 理解方法 | 哪个变化最值得看，哪些只是背景；什么不能省略 | 有来源的对象和关系、读者要回答的问题 |
| 使用素材库 | 每张参考借什么、不借什么、用在哪；图片先验还是可编辑组件 | 少量实际查看过的图片及各自职责 |
| 决定构图 | 总览＋展开、直接流程或前后对照，哪种适合这篇论文 | 推荐方案、取舍和有用的替代方案 |
| 形成候选 | 主次面积、连线含义、文字量、配色是否共同服务主线 | 包含具体设计决定和真实图片的生图输入 |
| 可编辑重建 | 保留认可的外观，纠正生成图的科学错误 | 可单独修改的文字、形状、概率格和连接 |
| 局部修改 | 用户选中了什么，问题来自什么，哪些必须保持 | 有明确范围的新版本与前后对比 |

具体判断见 [从方法到画法](references/art-direction.md)。例如，“太空”可能是容器过大，也可能是机制没有展开；两者不能都靠放大字号解决。“矩阵重复”应考虑带索引的局部行列，而不是删掉所有概率关系。Comic、Roman、Modern 分别协调字体、数学符号、线条和边界，不只是替换字体。

设计方案已经接入实际生图提示，不只存在说明文档里。[可运行示例](references/design-plan.md)演示同一机制选择两种不同构图，每次只准备其中一种。脚本不会自行读懂论文或判断美观；这些判断由助手结合原始资料、参考图和用户反馈完成。

## 怎样使用

把这个项目路径或后续 GitHub 链接交给助手，并说明：

> 使用 Astra Figure Workflow。论文和方法在……，素材库在……。制作输入到输出的方法图，文字少一些，使用 Comic / Roman / Modern 风格，交付可编辑 PPT。之后按我选中的局部修改，其他区域保持不变。

继续同一张图时，让助手读取已保存的绘图记录，无需重新描述每次修改。助手负责理解论文和操作当前可用工具；脚本保存版本并检查文件对应关系。它们不会自行调用付费 API、监听 PowerPoint 或自动发布材料。

具体运行与恢复说明见 [绘图记录和选区流程](references/workflow-session.md)。

## 当前能做什么

- 检索原创组件和已索引的私人 PPTX 素材。私人库按已有文本和标签检索，不是 OCR 或自动图像语义检索。
- 准备生图输入：科学要求、风格说明、**真实参考图片路径**、文件指纹和来源限制。实际生图仍需调用当前环境可用的图像工具，并遵循其技能说明。
- 将所选构图的区域安排、节点画法、科学连线、无箭头放大关系、字体配色和参考职责写入实际提示。设计不再匹配科学说明时，拒绝沿用旧输入。
- 从场景文件导出原生 PPTX：文字、线条和形状分别可编辑，不用整页截图替代。
- 根据稳定对象名称处理选区；修改被选对象，必要时只同步关联连线端点，并记录前后变化。
- 提供 Comic、Roman、Modern 三套风格，协调字体、线条和配色。
- 保存每次绘图的来源、当前文件、用户认可和检查记录；文件改变后，旧检查不会继续算作有效。
- 登记已认可、待选和已拒绝素材；指定主参考准备生图输入，保留真实图片和来源限制。
- 多页导出保留透明色块、虚线、斜体，以及绑定到该版本的对象对应表；已有输出不会被覆盖。

仓库包含 ODE、SDE、Flow Matching × 三种风格，共 **9 个基础演示组件**，用于功能测试，不作为默认审美参考。二维分布和三维网格的设计原则见 [参考与设计取舍](references/vector-field-priors.md)。私人论文、参考图片和实际案例不随仓库分发。

## 建议使用顺序

1. 读取论文方法和公式，确定视觉主线，记录必须出现、不得出现，以及仅为示意的内容。
2. 检索并实际查看少量素材，明确参考职责；比较有必要的不同构图，并给出推荐理由。
3. 将选定方案写进生图输入；简单局部修改直接编辑现有场景。
4. 根据确认方案重建可编辑对象，不能直接复制生成图里的科学错误。
5. 用对象选择或截图批注明确修改范围，保留已经确认的其他区域。
6. 检查最终尺寸下的图和实际 PPTX；嵌入论文时另外检查所在页与相邻页。

技能入口是 [SKILL.md](SKILL.md)。对象格式见 [scene-format.md](references/scene-format.md)，选区规则见 [local-editing.md](references/local-editing.md)。

## 本地使用

以下命令均从项目目录运行。检索、准备输入、定位对象及局部编辑入口已做实际测试。输出目录和文件请选择新的版本名。

### 检索与准备生图输入

从论文整理完设计后，可以不依赖旧演示组件：

```sh
python3 scripts/afw.py priors --brief examples/design-brief.json --design examples/design-plan.json --layout stacked --output-dir .local/runs/design-stacked-v1
```

这个原创教学示例不含私人论文或素材。真实方法图应替换为从当前论文整理的说明和设计，不能照搬示例机制。加入参考图片时，为每张图填写借用职责；字段和双布局例子见 [设计方案格式](references/design-plan.md)。

优先使用登记素材，不必选择旧组件：

```sh
python3 scripts/reference_registry.py register --id my-reference-v1 --path .local/references/my-reference.png --private --license unknown --status user-approved --approval-evidence '用户实际选择这张图的原话'
python3 scripts/afw.py search flow --include-private
python3 scripts/afw.py priors --brief .local/brief.json --reference-id my-reference-v1 --allow-private --output-dir .local/runs/my-figure/priors
```

多个 `--reference-id` 按顺序使用，第一张为主参考。已实际查看的新候选可以显式使用 `--allow-candidate-references`，但仍保留“候选”身份；已拒绝素材不会进入输入。不要为通过检查而编造用户认可。

原有演示命令继续保留：

```sh
python3 scripts/afw.py search ODE --style roman
python3 scripts/afw.py search "flow matching" --include-private
python3 scripts/afw.py priors --brief examples/ode-brief.json --component ode --style roman --output-dir .local/runs/ode-roman-v1
```

`priors` 生成 `prompt.txt`、`image-tool-input.json` 和 `manifest.json`，不会自行调用模型。检查其中每张参考图后，再使用图像工具支持的真实图片附件方式；仅在提示词里写文件名不算传入参考图。

`examples/ode-brief.json` 使用 `dx/dt = -x`。基础 ODE 组件中的一般轨迹**不代表这个具体方程的解**；目标图需要单调趋近平衡，不能照搬参考中的转向曲线。脚本不会自动判断这种科学冲突。

### 索引私人素材

```sh
python3 scripts/index_library.py --input /absolute/path/library.pptx --output-dir .local/library
```

索引和提取素材仅保存在 `.local/`，不修改原 PPTX。提取出的位图不是原生可编辑机制组件。索引不包含自动机制理解、母版继承元素重建或整页视觉分析。

默认私人检索读取 `.local/library/catalog.json`。原素材许可未知，不得直接公开或当作原创资产；上传到生图服务也应先确认授权。为生图输入显式选择私人图片时，需要同时使用 `--private-asset <索引中的资产ID>` 和 `--allow-private-references`，且输出仍须位于 `.local/`。

### 选中两个对象进行修改

完整绘图会话可根据真实对象名称自动准备选区请求并保留修改记录，见 [完整示例](references/workflow-session.md#selected-region-feedback)。下面是独立编辑器的低层入口：

```sh
python3 scripts/afw.py inspect-pptx --pptx output/components.pptx --slide 1
python3 scripts/selection_edit.py --scene components/ode/ode-comic.json --request examples/selection-request.json --output .local/ode-comic-v1.json
python3 scripts/build_components.py --scene .local/ode-comic-v1.json --output .local/ode-comic-v1.svg
```

示例请求只将 `initial-label` 和 `terminal-label` 下移 15。编辑器保留源文件，生成新场景和 `.audit.json`；已有输出会被拒绝。实际使用建议加入源文件的 `expected_sha256`，避免对过期版本执行批注。

对象名称需要先核对，不能把应用批注编号直接当成 PPTX 文件编号。截图选区仍需人工或模型识别到准确对象。文字修改会标记需要科学复核；改变科学语义颜色必须明确允许。

### 导出可编辑 PPTX

读取当前环境的 presentations 技能后，在依赖齐全的环境运行：

```sh
node scripts/export_components.mjs --scene .local/ode-comic-v1.json --output .local/exports/ode-comic-v1.pptx --build-dir .local/build
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

来源与公开限制见 [provenance.md](references/provenance.md)。私人素材、用户论文和本地记录不得随项目发布；发布工作流不等于获准发布使用它制作的私人案例。社交平台展示需要另行授权。
