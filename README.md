# platform-analysis

[**2. Class Age (Target Class Persistence)**](https://github.com/mapbiomas/platform-analysis/blob/main/analysis_1_age.js)
Description: Calculates the number of consecutive years that the pixel has belonged to the targetClass (e.g., Pasture), counting backwards from the last year of the series.

What it shows: This is crucial for identifying "old" vs. "recent" areas. For example, if the class is Pasture, a high value represents consolidated pasture, while a low value represents a recent conversion.

[**3. Class Frequency**]
Description: A temporal summary that counts the total number of years a pixel was classified as the targetClass throughout the entire time series (1985–2024).

What it shows: Unlike "Age," this does not require consecutive years. It reveals the recurrence of a class. A pixel might have a low "Age" but high "Frequency" if the class disappears and reappears over time (common in crop rotation or shifting cultivation).

[**4. Number of Distinct Classes**]
Description: This metric identifies how many different types of land use have occupied that specific pixel over the 40-year period.

What it shows: It is a proxy for land use diversity. A pixel with a value of "1" has only ever been one thing. A pixel with "5" has transitioned between five different categories (e.g., Forest -> Pasture -> Secondary Vegetation -> Agriculture -> Urban).

[**5. Number of Changes (Transitions)**]
Description: Calculates the total number of land cover transitions (runs) that occurred in the pixel.

What it shows: This measures landscape dynamism. High values indicate high instability or "flipping" between classes. For example, a pixel that changes from Forest to Pasture and then back to Forest would count as 2 changes.

[**6. Stable Classes**]
Description: Filters the map to show only the pixels that have remained the same class without a single change from 1985 to 2024.

What it shows: These are the "remnants" or "climax" areas. It is vital for identifying primary forests or long-term consolidated agricultural lands that have never been cleared or changed.

[**7. Class Last Year (Most Recent Occurrence)**]
Description: Identifies the latest calendar year in which the targetClass was detected in that pixel.

What it shows: It maps the temporal footprint of a class. If you are looking at "Fire" or "Deforestation," this layer tells you exactly when the most recent event happened in each specific location.

[**8. Accumulated Class (Spatial/Temporal Footprint)**]
Description: This layer represents the cumulative spatial extent of the targetClass across the entire time series (1985–2024). It identifies every pixel that was classified as the target category at least once during the study period.

What it shows: It maps the total footprint or "historical reach" of a specific land use. For example, if the target class is "Pasture," this layer shows all areas that have functioned as pasture at some point, even if they have since been abandoned or converted to another use. It is a powerful tool for analyzing the maximum expansion or the total area ever affected by a specific land cover type.
