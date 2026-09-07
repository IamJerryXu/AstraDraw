# 二维与曲面输运示例

这组原创几何示意展示二维分布输运，以及曲面上的输运。它们不是测量结果、训练输出或概率密度估计。色块与轮廓仅用于说明关系。曲面图是固定视角的可编辑二维投影，不能作为三维模型旋转。

外部风格参考的原始出版信息与许可未知，仓库不包含参考原图，也不授予其再分发许可。具体几何公式和科学解释保存在每份场景的 `scientific_notes` 中，并写入 PPT 备注。

| 文件 | 内容 |
| --- | --- |
| [planar.scene.json](planar.scene.json) | 二维分布输运，71 个独立对象 |
| [manifold.scene.json](manifold.scene.json) | 曲面输运，108 个独立对象 |
| [manifold-edited.scene.json](manifold-edited.scene.json) | 仅将曲面图右上角的 p₁ 标签下移 8 px |
| [move-label.json](move-label.json) | 可重复执行的单对象移动请求 |

[下载原版两页 PPT](../../output/showcase/spatial-flow.pptx) · [下载修改后两页 PPT](../../output/showcase/spatial-flow-edited.pptx)

矢量文件：[二维图](../../output/showcase/planar.svg) · [曲面图](../../output/showcase/manifold.svg) · [修改后的曲面图](../../output/showcase/manifold-edited.svg)

## 复现

在仓库根目录执行。PPT 导出需要项目说明中的 Codex 演示文稿运行环境及 `@oai/artifact-tool`。以下命令使用新目录，避免覆盖仓库中的演示文件。

```bash
mkdir -p .local/showcase-rebuild
python3 scripts/selection_edit.py \
  --scene examples/showcase/manifold.scene.json \
  --request examples/showcase/move-label.json \
  --output .local/showcase-rebuild/manifold-edited.scene.json

node scripts/export_components.mjs \
  --scene examples/showcase/planar.scene.json \
  --scene examples/showcase/manifold.scene.json \
  --output .local/showcase-rebuild/spatial-flow.pptx \
  --build-dir .local/showcase-build

node scripts/export_components.mjs \
  --scene examples/showcase/planar.scene.json \
  --scene .local/showcase-rebuild/manifold-edited.scene.json \
  --output .local/showcase-rebuild/spatial-flow-edited.pptx \
  --build-dir .local/showcase-build
```

修改前后第一页完全相同。第二页只有 `surface-target-label` 的纵坐标从 124 变为 132，曲面、网格、样本与路径均保持不变。对象表记录场景对象与 PPT 对象的对应关系；公开版本使用仓库相对路径。
