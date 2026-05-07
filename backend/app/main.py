from services.database import Base


# 自动创建表
Base.metadata.create_all(bind=engine)

def main():
    print("Hello from backend!")


if __name__ == "__main__":
    main()
