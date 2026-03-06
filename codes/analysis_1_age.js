/**
  Description: Calculates the number of consecutive years that the pixel
  has belonged to the targetClass (e.g., Pasture), counting backwards from
  the last year of the series.

  What it shows: This is crucial for identifying "old" vs. "recent" areas. 
  For example, if the class is Pasture, a high value represents consolidated 
  pasture, while a low value represents a recent conversion.
 */

// Define the MapBiomas asset path
var asset = 'projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1';

// Target class to be analyzed (e.g., 15 for Pasture in MapBiomas)
var targetClass = 15;

// Prefix used in the image band names
var bandPrefix = 'classification_';

// List of years available in the collection
var years = [
    1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992,
    1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000,
    2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008,
    2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016,
    2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024
];

// Load the multi-band image (each band represents a year)
var image = ee.Image(asset);

// Define a general spectral palette for continuous values
var palette = [
    "#a50026", "#d73027", "#f46d43", "#fdae61", "#fee08b",
    "#d9ef8b", "#a6d96a", "#66bd63", "#1a9850"
];

// Import MapBiomas official color modules
var Palettes = require('users/mapbiomas/modules:Palettes.js');
var paletteLulc = Palettes.get('classification9');

/**
 * Calculates the age (consecutive years) of a specific class.
 * @param {ee.Image} image - The multi-band LULC image.
 * @param {number} targetClass - The class value to calculate age for.
 * @param {Array} years - Array of years to iterate through.
 * @param {string} bandPrefix - Prefix of the band names.
 * @returns {ee.Image} - A single-band image representing the age in the final year.
 */
var getClassAge = function (image, targetClass, years, bandPrefix) {
    var classMask = ee.Image(image).eq(targetClass);
    var initialAge = ee.Image(0);

    // Iteratively calculate age year by year based on class persistence
    var ages = ee.List(years).iterate(
        function (year, previous) {
            year = ee.Number(year).format('%.0f');
            previous = ee.Image(previous);

            var currentImageBand = ee.String(bandPrefix).cat(year);
            var previousAgeBand = previous.bandNames().reverse().get(0);

            var currentImage = classMask.select([currentImageBand]).unmask(0);
            var previousAge = previous.select([previousAgeBand]);

            // If class exists, add 1 to previous age, otherwise reset to 0
            var currentAge = previousAge.add(1).multiply(currentImage)
                .rename(ee.String('age_').cat(year));

            return currentAge;
        }, initialAge);

    return ee.Image(ages).selfMask();
};

// --- Visualization Section ---

// Original LULC for the latest year
Map.addLayer(image, {
    bands: ['classification_2023'],
    min: 0, max: 69,
    palette: paletteLulc
}, 'LULC 2023', false);

// Class Age
var ages = getClassAge(image, targetClass, years, bandPrefix).selfMask();
Map.addLayer(ages, {
    min: 0, max: years.length,
    palette: palette
}, 'Class ' + String(targetClass) + ' Age');
