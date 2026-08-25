class EMAStrategy:

    def entry(self, row):

        return row["EMA20"] > row["EMA50"]

    def exit(self, row):

        return row["EMA20"] < row["EMA50"]