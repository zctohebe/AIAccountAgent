当前项目的背景以及需求：

Problem Statement Theme：AI-powered Business Process Automation
Problem Statement Title：AI Accounting Agent
Team Name：Guardians of Gal
Team Leader：Zhan, Changlian
Business Area：Accounting
WHAT
Project Overview
AI Accounting Agent is an intelligent accounting assistant designed to automate and streamline financial processes through an AI-driven interactive interface. It integrates multiple data sources, supports customized workflows, executes tasks automatically, and delivers results, helping organizations improve efficiency, accuracy, and flexibility in financial operations.
What it does
Provides an interactive accounting agent system.
Enables natural language interaction, enabling users to complete complex financial tasks through simple commands. Supports customized rules and automated execution to meet enterprise-specific needs.
WHY
Why
Increase Efficiency: Reduce manual operations and repetitive tasks.
Minimize Errors: Intelligent automation reduces human mistakes.
Improve Flexibility: Adapt to diverse financial workflows.
Cost Savings: Lower labor costs and accelerate financial processing.
Key Features
Key Features
Natural Language Command Execution:Users can input commands like "Run XXX report at 10 AM," and the AI schedules and executes automatically.
Scheduled Task Execution:Supports running tasks at specified times with automated processing and output.
Multi-Source Data Integration:Connects to ERP systems, financial platforms, Excel, databases, and more.
Automatic Result Storage:Saves each processed result to a designated local directory.
Custom Rule Management:Users can add new rules, and the AI confirms and enables them immediately.
Intelligent Anomaly Detection:Automatically identifies irregularities in financial data and alerts users.
Secure Data Processing:Ensures data confidentiality and complies with regulatory requirements.
Multi-Language Support:Enables global operations with support for multiple languages.
Note:
Not involving confidential client data; actual sample files cannot be provided, use templates or desensitized data for simulation.
Strictly comply with company data security and compliance requirements.


期望的架构:
架构组件
任务调度
使用 AWS EventBridge 或 Amazon Scheduler 定时触发 Lambda。
报表处理逻辑
报表存储在 S3，处理逻辑用 AWS Lambda 或 ECS。
每个报表处理逻辑可以注册为一个函数，支持动态扩展。
AI 分析与建议
调用 AWS Bedrock InvokeModel API 或 Converse API，传入报表数据和分析需求。
结果存储
保存到 S3 或本地数据库（如 DynamoDB 或 RDS）。
用户交互
前端可以是 Web 或桌面应用，通过 API 发指令。