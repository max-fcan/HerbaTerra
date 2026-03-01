# Summary of Modifications

**Date:** `2024-10-05`

**Author:** max-fcan

**Action Taken:** *Removed duplicate continent entries for affected country codes in the `iso3166_country_codes_continents.csv` data file. The output was stored in a new file called `iso3166_country_codes_continents_modified.csv`.*


## Plain Language Explanation
The modifications involved cleaning up the data file by **removing duplicate entries** for certain countries that were listed under multiple continents (using the *iso3166* standard). This ensures that each country is only **represented with a single continent** entry, **improving usability**.


## Summary
- **Azerbaijan** is now only listed under **Asia**.
- **Armenia** is now only listed under **Asia**.
- **Cyprus** is now only listed under **Asia**.
- **Georgia** is now only listed under **Asia**.
- **Kazakhstan** is now only listed under **Asia**.
- **United States Minor Outlying Islands** is now only listed under **Oceania**.
- **Russian Federation** is now only listed under **Europe**.
- **Turkey** is now only listed under **Asia**.


## Details of Changes
Removed duplicate continent entries for Azerbaijan (AZ), Armenia (AM), Cyprus (CY), Georgia (GE), Kazakhstan (KZ), United States Minor Outlying Islands (UM), Russian Federation (RU), and Turkey (TR) in the `iso3166_country_codes_continents_modified.csv` file.
The following lines were removed from the file:
- Europe, EU, "Azerbaijan, Republic of", AZ, AZE, 31
- Asia, AS, "Armenia", AM, ARM, 51
- Asia, AS, "Cyprus", CY, CYP, 196
- Asia, AS, "Georgia", GE, GEO, 268
- Asia, AS, "Kazakhstan", KZ, KAZ, 398
- Oceania, OC, "United States Minor Outlying Islands", UM, UMI, 581
- Europe, EU, "Russian Federation", RU, RUS, 643
- Asia, AS, "Turkey", TR, TUR, 792
