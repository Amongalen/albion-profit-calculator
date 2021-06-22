# Albion Profit Calculator
A website that calculates possible profits in Albion Online. 

There are 7 main cities and each city has a separate marketplace. A profit can be made by transporting goods between cities - buying cheap in one city and selling for more in a different one. 
Additionally, there is a lot of items that can be crafted. Each city specializes in crafting certain types of items - you will get some amount of ingredients back when crafting.
There is over 6500 different items in the game, over 10000 different upgrade/crafting recipes - there are quite a few possibilities for profits.

![obraz](https://user-images.githubusercontent.com/11869011/122793365-66c78080-d2bb-11eb-93ce-f274465d9d88.png)

### Disclaimer - some received prices data might be incorrect.

This tool helps in calculating what is more profitable in a given moment. It first loads data about all the items, recipes and such from a file - dump of game data stored in JSON file (really poor structure - probably converted from XML).
Prices for all the items are fetched from [The Albion Online Data Project API](https://www.albion-online-data.com/). There is a background task set to do it every X hours (currently twice a day).
When all possible combinations are calculated, the results can be accessed via website.

The project uses Flask for the web part and some NumPy for profit calculations.
