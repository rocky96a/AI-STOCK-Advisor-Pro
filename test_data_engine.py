from backend.data.data_engine import DataEngine


def main():

    engine = DataEngine()

    result = engine.build_universe(
        symbols=[
            "TCS.NS",
            "INFY.NS",
            "HDFCBANK.NS",
            "ICICIBANK.NS",
            "AXISBANK.NS",
        ],
        interval="1d",
        period="2y",
    )

    print()
    print("=" * 60)
    print("DATA ENGINE RESULT")
    print("=" * 60)

    for key, value in result.items():
        print(
            f"{key}: {value}"
        )


if __name__ == "__main__":
    main()