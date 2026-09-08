# 平面也可以有点波纹感

![确认风格的原稿](../../output/showcase-comic/planar-approved.png)

[可编辑 PPT](../../output/showcase-comic/planar-ripple.pptx) · [PPT 实际预览](../../output/showcase-comic/planar-ripple-previews/planar-ripple.png) · [SVG](../../output/showcase-comic/planar-ripple.svg) · [源文件](planar.scene.json)

这张的方向很简单：浅杏色和灰绿的两团分布，用赭色路径连接，背景留一点疏朗的波纹。没有水面光泽，也没有厚重描边。

上面是我们确认风格的生图原稿。PPT 是按照这个方向重新拆出来的版本，里面的波纹、色块、样本点、箭头和文字都可以单独改，不是把整张图片放进 PPT。微小纹理和轮廓不追求逐像素一致，实际效果可以看旁边的 PPT 预览。

## 想改哪里，直接说

把 PPT 或源文件交给 Astra，告诉它“背景线再淡一点”“右边色块换个颜色”，或者选中具体对象批注。已经满意的地方，也记得告诉它别动。

[对象对应表](../../output/showcase-comic/planar-ripple.object-map.json)保留了源文件与 PPT 元素的对应关系；具体环境和重建用法见[使用文档](../../docs/usage.md)，需要时让 Astra 读就好。

## 图里的含义

这里的 p₀、p₁ 是起点和终点分布的示意。点、色块和三条路径都不是实验数据；波纹不代表真实地形、势能或带数值的等高线，小箭头长度也不代表速度。

这版按照确认后的插画重建，不沿用旧版二维示例的解析方程，也不声称这些路径是某个微分方程的解。需要放进具体论文时，应让 Astra 根据论文的方法重新核对科学关系。

原稿由 imagegen 生成，可编辑版本由工作流重新构建。私人参考图未附带或嵌入。被否定的厚描边版和未确认的 Comic 三维草稿没有放进这里。
