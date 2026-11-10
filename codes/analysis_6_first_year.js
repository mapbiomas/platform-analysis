/**
  Description: Identifies the earliest year in which the pixel was classified
  as the targetClass.

  What it shows: When a class first appeared in each location. Together with
  the last year (analysis 7), it frames the period in which the class was present.
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
    "#fced79", "#f2eb0f", "#f2b963", "#d99632", "#d63422", "#5e0202"
];

// Import MapBiomas official color modules
var Palettes = require('users/mapbiomas/modules:Palettes.js');
var paletteLulc = Palettes.get('classification9');


/**
 * Identifies the earliest year a specific class was present in the pixel.
 * @param {ee.Image} image - The multi-band LULC image.
 * @param {number} targetClass - The class value.
 * @param {Array} years - Array of years.
 * @param {string} bandPrefix - Prefix of the band names.
 * @returns {ee.Image} - Image with the minimum year value found.
 */
var getClassFirstYear = function (image, targetClass, years, bandPrefix) {
    var image = ee.Image(image);

    var imageYears = years.map(
        function (year) {
            year = ee.Number(year);
            var bandName = ee.String(bandPrefix).cat(year.format('%.0f'));
            // selfMask: years outside the class are masked, otherwise their 0 would be the minimum
            var imageYear = image.select([bandName]).eq(ee.Image(targetClass)).multiply(year).selfMask();
            return imageYear;
        }
    );

    var firstYear = ee.Image(imageYears).reduce(ee.Reducer.min());
    return firstYear;
};

// --- Visualization Section ---

// Original LULC for the latest year
Map.addLayer(image, {
    bands: ['classification_2024'],
    min: 0, max: 69,
    palette: paletteLulc
}, 'LULC 2024', false);

// First occurrence year
var firstYear = getClassFirstYear(image, targetClass, years, bandPrefix);
Map.addLayer(firstYear, {
    min: 1985, max: 2024,
    palette: palette
}, 'Class ' + String(targetClass) + ' First Year');
