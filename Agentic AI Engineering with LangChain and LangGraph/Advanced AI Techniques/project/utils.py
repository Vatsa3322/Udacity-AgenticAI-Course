# reset_udahub.py
import os
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from contextlib import contextmanager
from langchain_core.messages import HumanMessage
from langgraph.graph.state import CompiledStateGraph


Base = declarative_base()

def reset_db(db_path: str, echo: bool = True):
    """Drops the existing udahub.db file and recreates all tables."""

    # Remove the file if it exists
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✅ Removed existing {db_path}")

    # Create a new engine and recreate tables
    engine = create_engine(f"sqlite:///{db_path}", echo=echo)
    Base.metadata.create_all(engine)
    print(f"✅ Recreated {db_path} with fresh schema")


@contextmanager
def get_session(engine: Engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def model_to_dict(instance):
    """Convert a SQLAlchemy model instance to a dictionary."""
    return {
        column.name: getattr(instance, column.name)
        for column in instance.__table__.columns
    }


def chat_interface(agent: CompiledStateGraph, ticket_id: str,
                   external_user_id: str | None = None, channel: str = "chat",
                   account_id: str = "cultpass"):
    """Interactive loop. Each turn sends ONLY the new human message; the conversation history is
    restored by the LangGraph checkpointer using thread_id (= ticket_id).
    `external_user_id` is the authenticated CultPass user id (e.g. 'f556c0')."""
    config = {"configurable": {"thread_id": ticket_id}}
    while True:
        user_input = input("User: ")
        print("User:", user_input)
        if user_input.lower() in ["quit", "exit", "q"]:
            print("Assistant: Goodbye!")
            break
        trigger = {
            "messages": [HumanMessage(content=user_input)],
            "external_user_id": external_user_id,
            "channel": channel,
            "account_id": account_id,
        }
        result = agent.invoke(input=trigger, config=config)
        print("Assistant:", result["messages"][-1].content)
