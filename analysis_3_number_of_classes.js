/**
 * Script to analyze Land Use and Land Cover (LULC) dynamics using MapBiomas data.
 * Calculates number of classes  in the time series.
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
var palette = ["#bababa", "#5417bd", "#11022b"];

// Import MapBiomas official color modules
var Palettes = require('users/mapbiomas/modules:Palettes.js');
var paletteLulc = Palettes.get('classification9');

/**
 * Calculates the number of unique classes present in a pixel over the years.
 * * @param {ee.Image} image - The multi-band LULC image.
 * @param {Array} years - Array of years.
 * @param {string} bandPrefix - Prefix of the band names.
 * @returns {ee.Image} - Image with count of distinct non-null classes.
 */
var getNumberOfClasses = function (image, years, bandPrefix) {
    var bands = ee.List(years).map(function (year) {
        year = ee.Number(year).format('%.0f');
        return ee.String(bandPrefix).cat(year);
    });

    var numberOfClasses = image.select(bands).reduce(ee.Reducer.countDistinctNonNull());
    return numberOfClasses;
};

// --- Visualization Section ---

// 1. Original LULC for the latest year
Map.addLayer(image, {
    bands: ['classification_2023'],
    min: 0, max: 69,
    palette: paletteLulc
}, 'LULC 2023', false);

// 4. Number of distinct classes
var numberOfClasses = getNumberOfClasses(image, years, bandPrefix).selfMask();
Map.addLayer(numberOfClasses, {
    min: 1, max: 6,
    palette: palette
}, 'Number of Classes');
