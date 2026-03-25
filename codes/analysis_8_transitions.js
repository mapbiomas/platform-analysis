// Define the MapBiomas asset path for the latest collection (Collection 10.1)
var asset = 'projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1';
var integration = ee.Image(asset);

// Import MapBiomas official color modules to ensure correct styling for LULC classes
var Palettes = require('users/mapbiomas/modules:Palettes.js');
var paletteLulc = Palettes.get('classification9');

// Define the temporal range for transition analysis
var start_year = 2008;
var end_year = 2024;

// Select specific classification bands for the chosen years
var img0 = integration.select('classification_' + start_year);
var img1 = integration.select('classification_' + end_year);

/**
 * Calculate transitions using map algebra: (Start Year * 100) + End Year.
 * This creates unique codes where the first digits represent the initial class 
 * and the last two digits represent the final class.
 */
var transitions = img0.multiply(100).add(img1).toInt16().rename('transitions');
    
// Display the original LULC map for the latest year (2024) as a reference layer
Map.addLayer(integration, {
    bands: ['classification_2024'],
    min: 0, max: 69,
    palette: paletteLulc
}, 'LULC 2024', false);

/**
 * Identify specific transition: Forest (3) to Pasture (15).
 * Resulting code: (3 * 100) + 15 = 315.
 * .selfMask() is used to make pixels that don't match the criteria transparent.
 */
var forest_to_pasture = transitions.eq(315).selfMask();
Map.addLayer(forest_to_pasture, {palette: '#ad0000'}, 'forest_'+start_year+' to pasture_'+ end_year);

/**
 * Identify multiple transitions to a single class (Regeneration):
 * 1503: Pasture (15) to Forest (03)
 * 2103: Agriculture/Mosaic (21) to Forest (03)
 * .remap() groups these different origins into a single value (1) for visualization.
 */
var pasture_or_mosaic_to_forest = transitions.remap([1503, 2103], [1, 1]);
Map.addLayer(pasture_or_mosaic_to_forest, {palette: '#27ff00'}, 'pasture_or_mosaic_'+start_year+' to forest_'+ end_year);
