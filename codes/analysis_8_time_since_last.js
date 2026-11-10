/**
  Description: Number of years between the last year in which the pixel was
  classified as the targetClass and the last year of the series.

  What it shows: How long ago a class left each location. 0 means the pixel is
  still in the class in the last year; pixels never in the class are transparent.
  It is the last year (analysis 7) expressed as elapsed time.
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

// Define a general spectral palette for continuous values (dark: recent, light: long ago)
var palette = [
    "#5e0202", "#d63422", "#d99632", "#f2b963", "#f2eb0f", "#fced79"
];

// Import MapBiomas official color modules
var Palettes = require('users/mapbiomas/modules:Palettes.js');
var paletteLulc = Palettes.get('classification9');


/**
 * Identifies the most recent year a specific class was present in the pixel.
 * @param {ee.Image} image - The multi-band LULC image.
 * @param {number} targetClass - The class value.
 * @param {Array} years - Array of years.
 * @param {string} bandPrefix - Prefix of the band names.
 * @returns {ee.Image} - Image with the maximum year value found; masked where never in class.
 */
var getClassLastYear = function (image, targetClass, years, bandPrefix) {
    var image = ee.Image(image);

    var imageYears = years.map(
        function (year) {
            year = ee.Number(year);
            var bandName = ee.String(bandPrefix).cat(year.format('%.0f'));
            var imageYear = image.select([bandName]).eq(ee.Image(targetClass)).multiply(year);
            return imageYear;
        }
    );

    var lastYear = ee.Image(imageYears).reduce(ee.Reducer.max()).selfMask();
    return lastYear;
};

/**
 * Years elapsed between the last occurrence of a class and the last year of the series.
 * @param {ee.Image} image - The multi-band LULC image.
 * @param {number} targetClass - The class value.
 * @param {Array} years - Array of years.
 * @param {string} bandPrefix - Prefix of the band names.
 * @returns {ee.Image} - 0 where the class is present in the last year; masked where never in class.
 */
var getTimeSinceLastOccurrence = function (image, targetClass, years, bandPrefix) {
    var lastYear = getClassLastYear(image, targetClass, years, bandPrefix);

    // No selfMask here: 0 (still in the class) must stay visible.
    // The mask of lastYear carries over, so pixels never in the class stay transparent.
    var timeSince = ee.Image(years[years.length - 1]).subtract(lastYear);
    return timeSince;
};

// --- Visualization Section ---

// Original LULC for the latest year
Map.addLayer(image, {
    bands: ['classification_2024'],
    min: 0, max: 69,
    palette: paletteLulc
}, 'LULC 2024', false);

// Years since the last occurrence
var timeSince = getTimeSinceLastOccurrence(image, targetClass, years, bandPrefix);
Map.addLayer(timeSince, {
    min: 0, max: years.length - 1,
    palette: palette
}, 'Class ' + String(targetClass) + ' Years Since Last');
