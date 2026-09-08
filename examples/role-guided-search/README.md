# 角色引导的演化搜索 Overview

从已有论文方法出发制作的可编辑方法图。此版本经使用者确认并获准公开作为 workflow demo，保留最终确认的布局、字体、配色和渐变箭头。

![方法 Overview](../../output/role-guided-search/overview.png)

**[下载可编辑 PPT](../../output/role-guided-search/overview.pptx)** · [SVG](../../output/role-guided-search/overview.svg) · [PNG](../../output/role-guided-search/overview.png) · [场景源文件](overview.scene.json) · [对象对应表](../../output/role-guided-search/overview.object-map.json)

## 图中表达什么

上半部从两个网络层提取节点重要性与角色表示，再建立跨层角色相似度。下半部使用一个共享种群进行角色引导的演化搜索，结合鲁棒评估、局部改进和先验更新，输出各任务的完整种子对。

- 蓝色与绿色区分两个网络层，每个种群个体同时包含两层的种子集合。
- `34 → 17` 表示跨层角色匹配，而 `Replaces 42` 表示替换第二层的种子，不是增加一个种子。
- DAT 与角色相似度在演化搜索期间保持固定。外围渐变箭头表示阶段阅读方向，不表示重新训练。
- 节点编号、矩阵、概率条及种子集合均为机制示意，不是实验测量或训练输出。

## 这个案例展示的工作流

局部反馈分别涉及 DAT、损失函数组和交叉变异区域。最终版本恢复了前两处原有样式，保留第三处的整理：父代、角色匹配和修复后子代分行呈现，去掉重复的替换小图，并留开文字与控制箭头的间距。

PPT 为一页，包含 606 个命名场景元素，文字、图形和连线均为独立对象，没有用整图截图代替可编辑内容。额外的箭头头部在导出时作为独立形状保存。Comic Sans MS 与 Times New Roman 未嵌入文件，缺少对应字体时，阅读软件可能替换字体。

已核对最终 PPT 与 SVG 预览，并测试单个文字对象的独立修改。恢复区域与修改前版本一致，其余区域与整理后的版本一致。连接线可编辑，但不保证在 PowerPoint 中任意拖动模块时自动跟随。

## 来源与公开范围

科学依据为使用者提供的论文 *Solving the Robust Influence Maximization Problem in Competitive Multilayer Networks via a Diffusion-Aware Role-Guided Evolutionary Approach*，Sections III–IV、Eqs. 1–19 与 Algorithm 1。仓库只展示获准公开的图，不包含论文全文。

外围渐变箭头与浅色背景参考 [DiffGDA Figure 1](https://arxiv.org/html/2602.10506v1#S4.F1) 的视觉设计，另见 [DiffGDA 项目](https://github.com/gxingyu/DiffGDA)。该参考只用于画面风格，不作为当前方法的科学依据，也未将其原图嵌入成品。

案例中的网络、芯片轮廓、种子格与放大镜由可编辑形状构成，没有嵌入第三方照片或图标文件。私人参考库、原始论文及对话批注未包含在公开文件中。获准展示此案例不等于授予论文、外部参考或整个项目的开放许可；本项目目前尚未指定整体开源许可证。

## 重新导出 PPT

在仓库根目录运行以下命令，输出到新的本地目录，不覆盖展示版本。需要项目说明中的 Codex 演示文稿环境与 `@oai/artifact-tool`。

```sh
node scripts/export_components.mjs \
  --scene examples/role-guided-search/overview.scene.json \
  --output .local/role-guided-search/output/overview.pptx \
  --build-dir .local/role-guided-search/build
```

对象对应表使用仓库相对路径，记录当前场景和 PPT 的文件指纹。重新导出或手工编辑后，应使用新生成的对应表，不沿用旧版指纹。
