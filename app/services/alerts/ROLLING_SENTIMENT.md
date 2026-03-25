## Two possible approaches to rolling sentiment calculation:

1. Equal-weight daily (Simple):
-> Mean of avg_sentiment over days that have a row
-> Ignores how many articles each day had

2. Article-weighted:
-> (\sum(\text{avg_sentiment}_d \times \text{article_count}_d) / \sum(\text{article_count}_d))
-> Better for when coverage varies a lot by day
=> This is the one that was implemented

## Days with no articles:
-> Should be excluded from calculation (treating them as 0 will dilute signal)