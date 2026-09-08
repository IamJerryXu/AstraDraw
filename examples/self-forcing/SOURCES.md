# 来源与使用说明

这是依据 [Self Forcing](https://arxiv.org/abs/2506.08009) 制作的方法示意图，经使用者确认后公开展示。采用论文的 chunk-wise、text-to-video、DMD 路径，不代表论文的全部训练选项，也不是原作者提供的官方配图。

科学依据：[论文 v2](https://arxiv.org/html/2506.08009v2) Sections 3.1–3.4、Algorithms 1–2 和附录，以及 [官方代码](https://github.com/guandeh17/Self-Forcing)。Fake score 的 Flow loss 依据 [utils/loss.py](https://github.com/guandeh17/Self-Forcing/blob/main/utils/loss.py) 中的 FlowPredLoss，目标为噪声减去停止梯度的生成 latent。

## 图与素材

- 文字、模块、连线、格子和概率示意均可在 PPT 中单独编辑。小鼠视频画面为 AI 生成的说明性插画，**不是 Self Forcing 的生成结果或实验数据**。
- 雪花使用 [Lucide snowflake](https://github.com/lucide-icons/lucide/blob/main/icons/snowflake.svg)，按 ISC 许可证使用，转换为蓝色透明 PNG。完整版权与许可见 [Lucide 许可](../paper-method/licenses/lucide-ISC.txt)。
- 火焰使用 [Twemoji fire](https://github.com/twitter/twemoji/blob/master/assets/svg/1f525.svg)，Copyright Twitter, Inc. and other contributors，按 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) 使用。原 SVG 转换为透明 PNG，并调整展示尺寸。许可说明见 [Twemoji](https://github.com/twitter/twemoji#license)。
- 雪花、火焰及小鼠画面是独立可替换的图片，不是可拆解的矢量图形；其余示意部分保留为 PPT 对象。
- 私人参考 PPT 仅用于布局与风格参考，未包含在公开文件中，也没有把其中的论文原图嵌入本图。

使用 Comic Sans MS 与 Times New Roman，未嵌入字体。其他电脑缺少这些字体时可能发生替换。连线可编辑，但任意拖动模块后不保证自动跟随。

本仓库目前未指定整体开源许可证。公开展示不改变第三方图标各自的许可，也不代表论文作者认可本图。
