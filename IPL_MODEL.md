# IPL player-value model: which players suit each team

Built from 1,243 matches of ball-by-ball data (2008 to 2026) plus the 2026 squads, salaries, ages and trades up to 11 Nov 2026. Run order: `build_dataset.py`, `build_players.py`, `build_trades.py`, `model_impact.py`, `model_predict.py`, `model_home.py`, `model_recommend.py`, `model_validate_wins.py`, `make_report.py`.

## The short version

- **Value** is measured as *impact*: runs above an average player over a season, ball by ball, compared with the same phase of the innings and the same ground, counting a wicket as 17 runs. Across 166 team-seasons, a team's total impact correlates **0.75** with its win rate; **+100 runs of impact is worth about 0.4 extra wins in a 14-game season.** Even the best signing moves a season by well under one win.
- **Forecasting next season is weak.** The model's rank correlation with what really happened is **0.16** (SE 0.02) over 14 test seasons, against 0.12 for 'same as last season' and 0.16 for a simple weighted 3-season average. It is no better than that simple average, and a typical forecast is off by about 66 runs of impact. Treat the forecasts as a ranking of broad tiers, not exact numbers.
- **Home-ground advantage is real for teams but not for individual players.** Across the ten franchises the home side wins about **54.6%** of matches against **48.9%** away, but differences between teams are within noise. A player's past record at a specific ground does **not** predict how he does there later (batting slope 0.01 ± 0.11, bowling 0.07 ± 0.11; a real effect would be near 1). So the recommendations do not use player-ground fit. Grounds are used only to remove their own scoring bias from every player's numbers.
- **Price is only loosely linked to value:** salary and forecast impact correlate about 0.4 across the 172 players with a forecast.

## How the recommendations are made

1. Each player's impact for every season is computed (`model_impact.py`).
2. A ridge-plus-gradient-boosting blend forecasts 2027 impact from the last three seasons, matches played, balls faced and bowled, and experience (`model_predict.py`). Age is not in the model: dates of birth exist only for the current squads.
3. For each team an optimiser picks the best squad and XI under the IPL rules, within the purse (`model_recommend.py`). Rules: squad of 18 to 25, at most 8 overseas in the squad and 4 in the XI, at least 2 keepers, 5 who bowl and 6 who bat in the XI, salaries within the purse. The purse defaults to ₹125 crore (the 2026 figure; 2027 is not confirmed: run `model_recommend.py 130` to change it). Cheap unproven fillers can always be signed at ₹0.30 crore.
4. **Keep value** = team value with the player minus without him. **Fit gain** = team value if an outside player is added (others may be dropped to fit the purse) minus now, at his current salary. These differ by team because they depend on what the team already has.

Targets are ideals, not predictions: several teams can want the same player, salaries in 2027 will differ, and who is available depends on the retention deadline (17 Nov), trades and the December auction.

## Summary by team

| Team | Squad now | Payroll (cr) | Best XI forecast (runs) | Best squad cost (cr) | Players not needed |
|---|---|---|---|---|---|
| Chennai Super Kings | 30 | 126.0 | 82.0 | 98.3 | 12 |
| Delhi Capitals | 26 | 113.6 | 190.0 | 69.6 | 8 |
| Gujarat Titans | 27 | 124.1 | 199.0 | 78.4 | 9 |
| Kolkata Knight Riders | 29 | 120.6 | 120.0 | 97.4 | 11 |
| Lucknow Super Giants | 26 | 108.0 | 90.0 | 65.7 | 8 |
| Mumbai Indians | 29 | 128.0 | 81.0 | 85.7 | 11 |
| Punjab Kings | 25 | 121.5 | 181.0 | 69.3 | 7 |
| Rajasthan Royals | 27 | 120.6 | 72.0 | 73.9 | 9 |
| Royal Challengers Bengaluru | 26 | 126.4 | 214.0 | 83.2 | 9 |
| Sunrisers Hyderabad | 29 | 119.6 | 164.0 | 89.9 | 11 |

The XI forecast is the sum of forecast impact of the best legal XI from the team's own players; higher is better.

## Chennai Super Kings

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Sanju Samson | Wicket-keeper batter | 32 | 18.0 | 31.0 | 31.6 |
| Shivam Dube | All-rounder | 33 | 12.0 | 26.0 | 26.8 |
| Ayush Mhatre | Batter | 19 | 0.3 | 12.0 | 12.5 |
| Ruturaj Gaikwad | Batter | 29 | 18.0 | 7.0 | 7.8 |
| Kartik Sharma | Batter | 20 | 14.2 | 5.0 | 6.2 |
| Prashant Veer | Batter | 20 | 14.2 | 0.0 | 1.2 |
| Kuldip Yadav | Bowler | 30 | 0.3 | 0.0 | 0.8 |
| Akash Madhwal | Wicket-keeper batter | 32 | 0.3 | 0.0 | 0.8 |
| Shreyas Gopal | All-rounder | 33 | 0.3 | 0.0 | 0.8 |
| Macneil Noronha | Bowler | 25 | 0.3 | 0.0 | 0.8 |
| Ramakrishna Ghosh | All-rounder | 29 | 0.3 | 0.0 | 0.8 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Noor Ahmad | Bowler | 21 | 10.0 | -12.0 |
| Anshul Kamboj | All-rounder | 25 | 3.4 | -11.0 |
| Gurjapneet Singh | Bowler | 28 | 2.2 | -9.0 |
| Dewald Brevis | Batter | 23 | 2.2 | -6.0 |
| Akeal Hosein | Bowler | 33 | 2.0 | -3.0 |
| Matt Henry | Bowler | 34 | 2.0 | -8.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 88.6 | 19.0 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 87.2 | 22.8 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 80.9 | 17.0 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 75.3 | 4.5 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 72.4 | 10.0 |

## Delhi Capitals

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| KL Rahul | Wicket-keeper batter | 34 | 14.0 | 72.0 | 72.8 |
| Tristan Stubbs | Batter | 26 | 10.0 | 49.0 | 49.4 |
| Ashutosh Sharma | Batter | 28 | 3.8 | 29.0 | 29.2 |
| David Miller | Batter | 37 | 2.0 | 27.0 | 27.0 |
| Rishabh Pant | Wicket-keeper batter | 29 | 15.0 | 7.0 | 7.4 |
| Sameer Rizvi | Batter | 22 | 0.9 | 6.0 | 6.1 |
| Tripurana Vijay | Bowler | 25 | 0.3 | 0.0 | 1.1 |
| Ajay Mandal | Bowler | 30 | 0.3 | 0.0 | 1.1 |
| Zeeshan Ansari | Bowler | 26 | 0.4 | 0.0 | 1.1 |
| Rehan Ahmed | Bowler | 22 | 0.8 | 0.0 | 0.4 |
| Dushmantha Chameera | Bowler | 34 | 0.8 | 0.0 | 0.4 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Axar Patel | All-rounder | 32 | 16.5 | -24.0 |
| Mitchell Starc | Bowler | 36 | 11.8 | -1.0 |
| Auqib Nabi | Bowler | 30 | 8.4 | -8.0 |
| Mukesh Kumar | Bowler | 33 | 8.0 | -8.0 |
| Nitish Rana | Batter | 32 | 4.2 | -4.0 |
| Abhishek Porel | Wicket-keeper batter | 24 | 4.0 | 0.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 83.8 | 11.2 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 83.2 | 26.3 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 76.8 | 20.6 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 71.2 | 8.1 |
| Shubman Gill | Gujarat Titans | Batter | 27 | 16.5 | 57.5 | 16.1 |

## Gujarat Titans

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Sai Sudharsan | Batter | 25 | 8.5 | 75.0 | 76.3 |
| Shubman Gill | Batter | 27 | 16.5 | 62.0 | 62.6 |
| Jos Buttler | Batter | 36 | 15.8 | 43.0 | 44.5 |
| Sai Kishore | Bowler | 30 | 2.0 | 11.0 | 11.6 |
| Prasidh Krishna | Bowler | 30 | 9.5 | 6.0 | 7.4 |
| Rahul Tewatia | All-rounder | 33 | 4.0 | 2.0 | 2.7 |
| Tom Banton | Wicket-keeper batter | 28 | 2.0 | 0.0 | 1.1 |
| Gurnoor Brar | Bowler | 26 | 1.3 | 0.0 | 1.1 |
| Jayant Yadav | Bowler | 36 | 0.8 | 0.0 | 1.1 |
| Ishant Sharma | Bowler | 38 | 0.8 | 0.0 | 1.1 |
| Anuj Rawat | Wicket-keeper batter | 27 | 0.3 | 0.0 | 1.1 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Rashid Khan | All-rounder | 28 | 18.0 | -13.0 |
| Kagiso Rabada | Bowler | 31 | 10.8 | -10.0 |
| Jason Holder | All-rounder | 35 | 7.0 | -10.0 |
| Shahrukh Khan | Batter | 31 | 4.0 | -4.0 |
| Washington Sundar | All-rounder | 27 | 3.2 | -6.0 |
| Glenn Phillips | Bowler | 29 | 2.0 | -4.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 89.6 | 21.0 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 88.1 | 24.8 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 81.8 | 19.0 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 73.4 | 12.0 |
| Tristan Stubbs | Delhi Capitals | Batter | 26 | 10.0 | 50.0 | 8.0 |

## Kolkata Knight Riders

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Rinku Singh | Batter | 29 | 13.0 | 37.0 | 36.7 |
| Sunil Narine | Bowler | 38 | 12.0 | 25.0 | 25.3 |
| Varun Chakravarthy | Bowler | 35 | 12.0 | 22.0 | 21.8 |
| Angkrish Raghuvanshi | Batter | 22 | 3.0 | 16.0 | 16.2 |
| Finn Allen | Batter | 27 | 2.0 | 11.0 | 11.0 |
| Tejasvi Singh | Wicket-keeper batter | 24 | 3.0 | 0.0 | 5.4 |
| Rovman Powell | Batter | 33 | 1.5 | 5.0 | 4.5 |
| Cameron Green | All-rounder | 27 | 25.2 | 3.0 | 3.4 |
| Manish Pandey | Batter | 37 | 0.8 | 1.0 | 1.2 |
| Akash Deep | Bowler | 29 | 1.0 | 0.0 | 0.0 |
| Daksh Kamra | All-rounder | 23 | 0.3 | 0.0 | 0.0 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Matheesha Pathirana | Bowler | 23 | 18.0 | 0.0 |
| Mustafizur Rahman | Bowler | 31 | 9.2 | 0.0 |
| Ramandeep Singh | Bowler | 29 | 4.0 | 0.0 |
| Harshit Rana | Bowler | 24 | 4.0 | 0.0 |
| Rachin Ravindra | Bowler | 26 | 2.0 | 0.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 87.2 | 2.3 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 86.3 | 6.8 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 80.0 | 1.0 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 74.4 | -11.5 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 73.6 | -6.7 |

## Lucknow Super Giants

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Nicholas Pooran | Batter | 31 | 21.0 | 41.0 | 43.4 |
| Josh Inglis | Wicket-keeper batter | 31 | 8.6 | 29.0 | 30.9 |
| Mitchell Marsh | All-rounder | 35 | 3.4 | 18.0 | 19.7 |
| Mukul Choudhary | Batter | 22 | 2.6 | 3.0 | 5.8 |
| Ayush Badoni | Batter | 26 | 4.0 | 0.0 | 3.1 |
| Naman Tiwari | Bowler | 21 | 1.0 | 0.0 | 2.7 |
| Arjun Tendulkar | Bowler | 27 | 0.3 | 0.0 | 2.7 |
| Arshin Kulkarni | Bowler | 21 | 0.3 | 0.0 | 2.7 |
| Akash Singh | Bowler | 24 | 0.3 | 0.0 | 2.7 |
| Wanindu Hasaranga | All-rounder | 29 | 2.0 | 0.0 | 2.0 |
| Himmat Singh | Bowler | 30 | 0.3 | -1.0 | 1.8 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Kuldeep Yadav | Bowler | 31 | 13.5 | -6.0 |
| Mayank Yadav | Bowler | 24 | 11.0 | -4.0 |
| Mohammed Shami | Bowler | 36 | 10.0 | -16.0 |
| Avesh Khan | Bowler | 29 | 9.8 | -8.0 |
| Abdul Samad | Batter | 25 | 4.2 | -3.0 |
| Mohsin Khan | Bowler | 28 | 4.0 | -9.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 89.8 | 22.0 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 89.0 | 25.8 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 82.7 | 20.0 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 77.1 | 7.5 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 74.3 | 13.0 |

## Mumbai Indians

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Ryan Rickelton | Wicket-keeper batter | 30 | 1.0 | 21.0 | 21.5 |
| Suryakumar Yadav | Batter | 36 | 16.4 | 21.0 | 21.4 |
| Tilak Varma | Batter | 24 | 8.0 | 17.0 | 17.2 |
| Sherfane Rutherford | Batter | 28 | 2.6 | 8.0 | 7.9 |
| Jasprit Bumrah | Bowler | 32 | 18.0 | 7.0 | 7.0 |
| Mitchell Santner | All-rounder | 34 | 2.0 | 3.0 | 3.1 |
| Naman Dhir | All-rounder | 26 | 5.2 | 2.0 | 2.5 |
| Rohit Sharma | Batter | 39 | 16.3 | 1.0 | 1.6 |
| Trent Boult | Bowler | 37 | 12.5 | 1.0 | 1.2 |
| Robin Minz | Wicket-keeper batter | 24 | 0.7 | 0.0 | 0.9 |
| Atharva Ankolekar | All-rounder | 26 | 0.3 | 0.0 | 0.3 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Arshdeep Singh | Bowler | 27 | 18.0 | -5.0 |
| Deepak Chahar | Bowler | 34 | 9.2 | -6.0 |
| Will Jacks | Batter | 27 | 5.2 | -1.0 |
| Allah Ghazanfar | Bowler | 20 | 4.8 | -5.0 |
| Shardul Thakur | Bowler | 35 | 2.0 | -14.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 87.9 | 22.4 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 87.2 | 26.0 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 80.9 | 20.2 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 75.3 | 7.8 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 72.4 | 13.4 |

## Punjab Kings

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Shreyas Iyer | Batter | 31 | 26.8 | 87.0 | 88.6 |
| Prabhsimran Singh | Batter | 26 | 4.0 | 30.0 | 31.4 |
| Shashank Singh | Batter | 34 | 5.5 | 24.0 | 25.5 |
| Cooper Connolly | All-rounder | 23 | 3.0 | 16.0 | 17.4 |
| Marcus Stoinis | All-rounder | 37 | 11.0 | 13.0 | 14.0 |
| Priyansh Arya | Batter | 25 | 3.8 | 9.0 | 10.5 |
| Suryansh Shedge | All-rounder | 23 | 0.3 | 1.0 | 2.8 |
| Yash Thakur | Bowler | 27 | 1.6 | 0.0 | 1.4 |
| Vishnu Vinod | Wicket-keeper batter | 32 | 0.9 | 0.0 | 1.4 |
| Praveen Dubey | Bowler | 33 | 0.3 | 0.0 | 1.4 |
| Pyla Avinash | Bowler | 26 | 0.3 | 0.0 | 1.4 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Hardik Pandya | All-rounder | 33 | 18.0 | -15.0 |
| Yuzvendra Chahal | Bowler | 36 | 18.0 | -8.0 |
| Marco Jansen | Bowler | 26 | 7.0 | -28.0 |
| Nehal Wadhera | Batter | 26 | 4.2 | -9.0 |
| Azmatullah Omarzai | Bowler | 26 | 2.4 | -8.0 |
| Lockie Ferguson | Bowler | 35 | 2.0 | -5.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 89.9 | 21.0 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 82.1 | 19.0 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 76.5 | 6.5 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 73.7 | 12.0 |
| Shubman Gill | Gujarat Titans | Batter | 27 | 16.5 | 62.8 | 14.5 |

## Rajasthan Royals

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Dhruv Jurel | Wicket-keeper batter | 25 | 14.0 | 28.0 | 28.1 |
| Riyan Parag | All-rounder | 25 | 14.0 | 18.0 | 18.0 |
| Ravindra Jadeja | All-rounder | 37 | 14.0 | 14.0 | 14.1 |
| Donovan Ferreira | Wicket-keeper batter | 28 | 1.0 | 8.0 | 7.9 |
| Yashasvi Jaiswal | Batter | 24 | 18.0 | 6.0 | 5.9 |
| Sam Curran | All-rounder | 28 | 2.4 | 0.0 | 0.4 |
| Kwena Maphaka | Bowler | 20 | 1.5 | 0.0 | 0.4 |
| Yudhvir Singh | Bowler | 29 | 0.3 | 0.0 | 0.4 |
| Lhuan-dre Pretorius | Batter | 20 | 0.3 | 0.0 | 0.4 |
| Sushant Mishra | Bowler | 25 | 0.3 | 0.0 | 0.4 |
| Emanjot Chahal | Bowler | 22 | 0.3 | 0.0 | 0.4 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Jofra Archer | Bowler | 31 | 12.5 | -7.0 |
| Shimron Hetmyer | Batter | 29 | 11.0 | -3.0 |
| Ravi Bishnoi | Bowler | 26 | 7.2 | -23.0 |
| Tushar Deshpande | Bowler | 31 | 6.5 | -7.0 |
| Sandeep Sharma | Bowler | 33 | 4.0 | -3.0 |
| Nandre Burger | Bowler | 31 | 3.5 | -2.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 88.6 | 20.6 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 87.2 | 24.4 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 80.9 | 18.6 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 75.3 | 6.1 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 72.4 | 11.6 |

## Royal Challengers Bengaluru

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Virat Kohli | Batter | 38 | 21.0 | 81.0 | 80.4 |
| Rajat Patidar | Batter | 33 | 11.0 | 36.0 | 35.6 |
| Venkatesh Iyer | Batter | 31 | 7.0 | 34.0 | 33.7 |
| Tim David | Batter | 30 | 3.0 | 26.0 | 25.2 |
| Bhuvneshwar Kumar | Bowler | 36 | 10.8 | 19.0 | 18.8 |
| Phil Salt | Batter | 30 | 11.5 | 17.0 | 17.0 |
| Jordan Cox | Wicket-keeper batter | 26 | 0.8 | 0.0 | 5.4 |
| Krunal Pandya | All-rounder | 35 | 5.8 | 1.0 | 0.8 |
| Swapnil Singh | Bowler | 35 | 0.5 | 0.0 | 0.0 |
| Kanishk Chouhan | All-rounder | 20 | 0.3 | 0.0 | 0.0 |
| Vicky Ostwal | All-rounder | 24 | 0.3 | 0.0 | 0.0 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Josh Hazlewood | Bowler | 35 | 12.5 | -5.0 |
| Jitesh Sharma | Wicket-keeper batter | 33 | 11.0 | -13.0 |
| Rasikh Salam | Bowler | 26 | 6.0 | -13.0 |
| Mangesh Yadav | All-rounder | 4 | 5.2 | 0.0 |
| Yash Dayal | Bowler | 28 | 5.0 | 0.0 |
| Suyash Sharma | Bowler | 23 | 2.6 | -14.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 90.0 | 22.7 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 74.1 | 21.5 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 73.8 | 13.7 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 62.2 | 3.3 |
| Shubman Gill | Gujarat Titans | Batter | 27 | 16.5 | 48.4 | 11.3 |

## Sunrisers Hyderabad

**Best XI from the current squad** (by contribution):

| Player | Role | Age | Salary (cr) | Forecast impact | Keep value |
|---|---|---|---|---|---|
| Heinrich Klaasen | Wicket-keeper batter | 35 | 23.0 | 89.0 | 91.7 |
| Abhishek Sharma | All-rounder | 26 | 14.0 | 39.0 | 41.9 |
| Ishan Kishan | Wicket-keeper batter | 28 | 11.2 | 29.0 | 31.7 |
| Travis Head | Batter | 32 | 14.0 | 5.0 | 7.7 |
| Nitish Kumar Reddy | All-rounder | 23 | 6.0 | 0.0 | 3.1 |
| Krains Fuletra | All-rounder | 22 | 0.3 | 0.0 | 3.1 |
| Khaleel Ahmed | Bowler | 28 | 4.8 | 3.0 | 3.0 |
| Harshal Patel | Bowler | 35 | 8.0 | 0.0 | 0.3 |
| Eshan Malinga | Bowler | 25 | 1.2 | 0.0 | 0.2 |
| RS Ambrish | Bowler | 19 | 0.5 | 0.0 | 0.0 |
| Smaran Ravichandran | Bowler | 23 | 0.3 | 0.0 | 0.0 |

**Paid well but not needed by this model** (forecast below what a cheap replacement gives, or surplus to the best squad):

| Player | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|
| Pat Cummins | Bowler | 33 | 18.0 | -7.0 |
| Harshal Patel | Bowler | 35 | 8.0 | 0.0 |
| T. Natarajan | Bowler | 35 | 5.0 | -11.0 |
| Nathan Ellis | Bowler | 32 | 2.0 | 0.0 |
| Gerald Coetzee | Bowler | 26 | 2.0 | 0.0 |

**Best additions** (if available):

| Player | Now at | Role | Age | Salary (cr) | Fit gain | Extra cost (cr) |
|---|---|---|---|---|---|---|
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 87.2 | 20.0 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 80.9 | 14.2 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 75.3 | 1.8 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 72.4 | 7.2 |
| Shubman Gill | Gujarat Titans | Batter | 27 | 16.5 | 61.5 | 9.8 |

## League-wide

**Highest forecast impact for 2027:**

| Player | Team | Role | Age | Salary (cr) | Forecast impact |
|---|---|---|---|---|---|
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 88.6 |
| Shreyas Iyer | Punjab Kings | Batter | 31 | 26.8 | 87.2 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 80.9 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 75.3 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 72.4 |
| Shubman Gill | Gujarat Titans | Batter | 27 | 16.5 | 61.5 |
| Tristan Stubbs | Delhi Capitals | Batter | 26 | 10.0 | 49.1 |
| Jos Buttler | Gujarat Titans | Batter | 36 | 15.8 | 43.4 |
| Nicholas Pooran | Lucknow Super Giants | Batter | 31 | 21.0 | 41.2 |
| Abhishek Sharma | Sunrisers Hyderabad | All-rounder | 26 | 14.0 | 38.8 |
| Rinku Singh | Kolkata Knight Riders | Batter | 29 | 13.0 | 36.7 |
| Rajat Patidar | Royal Challengers Bengaluru | Batter | 33 | 11.0 | 36.1 |

**Best value for money** (forecast impact above 25, most impact per crore):

| Player | Team | Role | Age | Salary (cr) | Forecast impact | Impact per cr |
|---|---|---|---|---|---|---|
| David Miller | Delhi Capitals | Batter | 37 | 2.0 | 26.6 | 13.3 |
| Sai Sudharsan | Gujarat Titans | Batter | 25 | 8.5 | 75.3 | 8.9 |
| Tim David | Royal Challengers Bengaluru | Batter | 30 | 3.0 | 25.7 | 8.6 |
| Ashutosh Sharma | Delhi Capitals | Batter | 28 | 3.8 | 28.8 | 7.6 |
| Prabhsimran Singh | Punjab Kings | Batter | 26 | 4.0 | 30.0 | 7.5 |
| KL Rahul | Delhi Capitals | Wicket-keeper batter | 34 | 14.0 | 72.4 | 5.2 |
| Venkatesh Iyer | Royal Challengers Bengaluru | Batter | 31 | 7.0 | 34.2 | 4.9 |
| Tristan Stubbs | Delhi Capitals | Batter | 26 | 10.0 | 49.1 | 4.9 |
| Heinrich Klaasen | Sunrisers Hyderabad | Wicket-keeper batter | 35 | 23.0 | 88.6 | 3.9 |
| Virat Kohli | Royal Challengers Bengaluru | Batter | 38 | 21.0 | 80.9 | 3.9 |

**Highest-paid players with the weakest forecast.** Mostly one poor 2026 season pulling the forecast down; check the player's longer record before acting:

| Player | Team | Role | Age | Salary (cr) | Forecast impact | 2026 impact |
|---|---|---|---|---|---|---|
| Axar Patel | Delhi Capitals | All-rounder | 32 | 16.5 | -23.6 | -39.5 |
| Mohammed Shami | Lucknow Super Giants | Bowler | 36 | 10.0 | -16.2 | -77.0 |
| Hardik Pandya | Punjab Kings | All-rounder | 33 | 18.0 | -15.1 | -114.2 |
| Jitesh Sharma | Royal Challengers Bengaluru | Wicket-keeper batter | 33 | 11.0 | -13.4 | -90.5 |
| Rashid Khan | Gujarat Titans | All-rounder | 28 | 18.0 | -12.9 | 51.9 |
| Noor Ahmad | Chennai Super Kings | Bowler | 21 | 10.0 | -11.7 | -36.6 |
| Kagiso Rabada | Gujarat Titans | Bowler | 31 | 10.8 | -10.3 | 180.7 |
| Yuzvendra Chahal | Punjab Kings | Bowler | 36 | 18.0 | -7.8 | -1.5 |
| Jofra Archer | Rajasthan Royals | Bowler | 31 | 12.5 | -7.5 | 90.9 |
| Pat Cummins | Sunrisers Hyderabad | Bowler | 33 | 18.0 | -7.1 | -50.3 |

## What the model cannot see

- Fielding, wicket-keeping quality, captaincy, injuries and fitness, and who bats where. Keepers and bowlers are valued only by their batting and bowling.
- Age: older players (Kohli 38, Klaasen 35, Jadeja 37) are forecast like younger ones with the same record.
- Match-ups, pitch type versus bowling style, and dew. Ground effects are measured only as an overall scoring level.
- Auction rules for 2027 (purse, retention slabs, overseas fee cap, right to match) are not confirmed, and 2027 salaries will differ from 2026 contracts.
- Role labels for about 40 players with almost no IPL record are guesses, and players with no 2026 usage are forecast at league average.
- A sample of one season for most players: the forecast error (about 66 runs) is larger than the gap between most mid-ranked players.
