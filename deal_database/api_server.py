import yaml
import re
import asyncio
from typing import List, Union, Dict, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
import uvicorn


def get_db_config(yaml_file='settings.yaml') -> Dict[str, Any]:
    """读取配置并构建 SQLAlchemy 需要的数据库 URL"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        raise RuntimeError(f"配置文件 {yaml_file} 未找到，请确保文件存在。")

    db_config = config['database']
    pool_config = db_config.get('pool', {})
    
    # 构建异步连接 URL
    database_url = (
        f"postgresql+asyncpg://{db_config['user']}:{db_config['password']}"
        f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
    )
    
    return {
        "url": database_url,
        "table_name": db_config['table_name'],
        "pool_size": pool_config.get('min_connections', 4),
        "max_overflow": pool_config.get('max_connections', 10) - pool_config.get('min_connections', 4),
        "pool_recycle": pool_config.get('pool_recycle', 3600),
        "command_timeout": pool_config.get('command_timeout', 10),
    }


# 全局变量
async_engine = None
AsyncSessionLocal = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    生命周期管理：初始化数据库连接池
    """
    global async_engine, AsyncSessionLocal
    
    # 读取配置
    config = get_db_config()
    table_name = config.pop("table_name")
    db_url = config.pop("url")
    
    # 创建异步引擎
    print("正在初始化数据库连接池...")
    async_engine = create_async_engine(
        db_url,
        pool_size=config["pool_size"],
        pool_recycle=config["pool_recycle"],     # 定期回收连接
        max_overflow=config["max_overflow"],
        
        # 每次从池中取连接前先 Ping 一下，坏了自动重连
        pool_pre_ping=True,
        
        # 设置底层 asyncpg 的命令超时时间
        connect_args={
            "server_settings": {
                "jit": "off",       # 关闭 JIT 往往能提高简单查询的稳定性
            },
            "command_timeout": config["command_timeout"]   # 从配置读取 SQL 执行超时时间
        },
        echo=False
    )
    
    # 创建会话工厂
    AsyncSessionLocal = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )
    
    # 将表名存入 app.state 供后续使用
    app.state.table_name = table_name
    print(f"数据库异步引擎已启动 (Table: {table_name}, Timeout: {config['command_timeout']}s, Pre-ping: ON)")
    
    yield
    
    # 关闭引擎
    if async_engine:
        await async_engine.dispose()
        print("数据库异步引擎已关闭")


app = FastAPI(
    title="恶意代码搜索 API (Async)",
    description="基于 SQLAlchemy + Asyncpg 的高性能搜索 (已修复连接问题)",
    version="2.1.0",
    lifespan=lifespan
)

# 确保回滚和资源释放
async def get_db():
    if AsyncSessionLocal is None:
        raise HTTPException(status_code=503, detail="Database not initialized")
    
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            # 发生异常时强制回滚，防止事务卡死
            await session.rollback()
            raise e
        finally:
            await session.close()


class SearchRequest(BaseModel):
    code_strings: Union[str, List[str]]
    
    class Config:
        json_schema_extra = {
            "example": {
                "code_strings": ["print('hello')", "import os"]
            }
        }

class RecordModel(BaseModel):
    id: int
    file_name: Union[str, None] = None
    title: Union[str, None] = None
    malicious_code: Union[str, None] = None
    description: Union[str, None] = None
    hash_str: Union[str, None] = None

class ResultItemModel(BaseModel):
    code_string: str
    records: List[RecordModel]
    count: int

class SearchResponse(BaseModel):
    state: str
    message: str
    data: List[ResultItemModel]
    count: int


@app.post("/search", response_model=SearchResponse)
async def search_malicious_code(
    request: SearchRequest, 
    session: AsyncSession = Depends(get_db)
):
    """
    搜索恶意代码
    """
    code_strings = [request.code_strings] if isinstance(request.code_strings, str) else request.code_strings
    
    table_name = app.state.table_name
    all_results = []
    
    try:
        # 子串匹配查询：数据库中的 format_code 是输入代码的子串
        # 即：输入代码包含数据库中的代码
        sql_template = text(f"""
            SELECT id, file_name, title, malicious_code, description, hash_str
            FROM {table_name}
            WHERE :input_code LIKE CONCAT('%', format_code, '%')
        """)

        for code_str in code_strings:
            # 去除空格用于匹配
            cleaned_code = re.sub(r'[\s\n]+', '', code_str)
            
            # 执行异步查询：查找所有 format_code 是 cleaned_code 子串的记录
            result = await session.execute(sql_template, {"input_code": cleaned_code})
            
            # 获取结果
            rows = result.mappings().all()
            
            # 组装数据
            if rows:
                records = [
                    RecordModel(
                        id=row['id'],
                        file_name=row['file_name'],
                        title=row['title'],
                        malicious_code=row['malicious_code'],
                        description=row['description'],
                        hash_str=row['hash_str']
                    ) for row in rows
                ]
                
                all_results.append(ResultItemModel(
                    code_string=code_str,
                    records=records,
                    count=len(records)
                ))

        # 构造最终响应
        if all_results:
            return SearchResponse(
                state='success',
                message=f'查询成功，找到 {len(all_results)} 个代码字符串的匹配数据',
                data=all_results,
                count=len(all_results)
            )
        else:
            return SearchResponse(
                state='not_found',
                message='所有代码字符串均未找到匹配的恶意代码',
                data=[],
                count=0
            )

    except asyncio.TimeoutError:
        # 捕获 asyncpg 的超时错误
        print("Error: Database query timed out.")
        raise HTTPException(status_code=504, detail="Database query timed out")
    except SQLAlchemyError as e:
        import traceback
        print(f"Database Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Database query error")
    except Exception as e:
        import traceback
        print(f"Server Error: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    # 读取 API 服务器配置
    with open('settings.yaml', 'r', encoding='utf-8') as f:
        settings = yaml.safe_load(f)
    api_config = settings.get('api_server', {})
    host = api_config.get('host', '0.0.0.0')
    port = api_config.get('port', 8000)
    
    uvicorn.run(app, host=host, port=port)