# Contributing / 贡献指南

Thanks for helping improve this research project.

感谢你帮助改进这个研究项目。

## Development / 开发流程

1. Create a virtual environment.
2. Install the package with `python -m pip install -e .`.
3. Run `python -m unittest discover -s tests -v`.
4. If strategy behavior, reporting, or data assumptions changed, rerun the baseline script and update `TEST_REPORT.md`.

1. 创建虚拟环境。
2. 使用 `python -m pip install -e .` 安装本项目。
3. 运行 `python -m unittest discover -s tests -v`。
4. 如果改动影响策略行为、报告或数据假设，请重新运行基线脚本并更新 `TEST_REPORT.md`。

## Pull Requests / Pull Request 要求

- Keep strategy-behavior changes separate from packaging or documentation changes when possible.
- Include the exact command used for validation.
- Do not add broker or vendor data unless redistribution is permitted.
- State whether the change affects historical results.

- 尽量把策略行为变更与工程包装、文档变更分开提交。
- 写明用于验证的完整命令。
- 未确认再分发授权前，不要加入券商或供应商数据。
- 说明改动是否影响历史回测结果。

## Research Standards / 研究标准

Backtest improvements should include the dataset, timeframe, parameters, metrics, and limitations. Historical performance should never be described as a guaranteed future result.

回测改进应包含数据集、周期、参数、指标和局限性。不得把历史表现描述为未来收益保证。
