# 原创可编辑组件 v0.1

本目录包含 ODE、SDE、Flow Matching 各三种风格，共 9 个场景。每个场景的 JSON 是编辑源，SVG 保留文本与对象 ID，PPTX 中各条轨迹、箭头、状态点和文字均为原生可编辑对象。

## 科学含义

- ODE：不同初值在适当正则性条件下各自沿唯一轨迹演化，无分支。横轴为时间，竖向位置为示意状态坐标。
- SDE：同一初值在不同噪声实现下可产生不同轨迹。当前折线路径仅为原创示意，不是 Brownian 或 SDE 数值模拟。
- Flow Matching：训练区展示一种条件直线插值及其目标速度；采样区展示学习速度场的 ODE 积分。训练配对不代表采样时可访问目标，也不指定配对算法。

每个场景的 `scientific_notes` 和 PPTX 备注保存适用范围。三种风格不改变文字、对象数量或科学含义。它们实际改变字体、配色和线宽。圆角参数供包含模块框的后续组件使用，本批开放流图未强行增加框体。

## 重建与局部修改

```sh
python3 scripts/build_components.py
node scripts/export_components.mjs
```

生成全部场景会覆盖本目录的派生版本。局部编辑应另存 JSON，并单独导出，避免覆盖确认过的修改：

```sh
python3 scripts/build_components.py --scene edited.json --output edited.svg
node scripts/export_components.mjs --scene edited.json --output output/edited.pptx
```

PPTX 旁的 `*.object-map.json` 对应交付文件中的实际页码、形状编号、名称和场景对象 ID。箭头尖是独立可编辑对象，映射回其所属连线。此版本不承诺 PowerPoint 拖动时自动附着连接，也不将 PPTX 手工修改自动回写至 JSON。

目录中的几何、布局和文字由本项目原创，`license: original-project` 表示来源分类，具体使用许可由仓库许可证决定。未复用 Mingzhe 或私人素材库中的未知许可素材。
