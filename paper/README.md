# paper 论文初稿目录说明

本目录为全国大学生数学建模竞赛风格的 LaTeX 初稿结构，已按 A 题场景写入章节框架与核心公式。

## 文件结构

- `main.tex`：主文档入口
- `sections/`：分章节正文
- `refs.bib`：参考文献库

## 编译方式（本地安装 TeX Live / MiKTeX 后）

推荐：

```bash
latexmk -xelatex -interaction=nonstopmode -file-line-error main.tex
```

或手动：

```bash
xelatex main.tex
bibtex main
xelatex main.tex
xelatex main.tex
```

## 后续完善建议

1. 将程序输出图件复制到 `results/figures/` 或 `paper/figures/` 并替换占位图名。
2. 在 `06_solution_results.tex` 中填入真实实验数据。
3. 按最终队伍信息更新标题页。
