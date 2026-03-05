/**
 * 
 */
var asset = 'projects/mapbiomas-public/assets/brazil/lulc/collection10_1/mapbiomas_brazil_collection10_1_coverage_v1'

var targetClass = 15;

var bandPrefix = 'classification_';

// Lista de anos
var years = [
    1985, 1986, 1987, 1988, 1989, 1990, 1991, 1992,
    1993, 1994, 1995, 1996, 1997, 1998, 1999, 2000,
    2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008,
    2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016,
    2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024
];

var image = ee.Image(asset);

var palette = [
    "#a50026",
    "#d73027",
    "#f46d43",
    "#fdae61",
    "#fee08b",
    "#d9ef8b",
    "#a6d96a",
    "#66bd63",
    "#1a9850"
].reverse();

var Palettes = require('users/mapbiomas/modules:Palettes.js');

var paletteLulc = Palettes.get('classification9');

var getClassAge = function (image, targetClass, years, bandPrefix) {
    /**
     * Calcula a idade de uma classe específica em uma imagem de uso do solo.
     * 
     * @param {ee.Image}
     image - A imagem de uso do solo contendo as classes.
     * @param {number}
     targetClass - A classe alvo para a qual a idade será calculada.
     * @param {Array}
     years - Lista de anos para calcular a idade.
     * @param {string}
     bandPrefix - Prefixo dos nomes das bandas na imagem.
     * @returns {ee.Image} - Imagem com a idade da classe alvo para cada ano.
     */
    var classMask = ee.Image(image).eq(targetClass);

    var initialAge = ee.Image(0);

    // Iteração para calcular a idade da SV ano a ano
    var ages = ee.List(years).iterate(
        function (year, previous) {
            year = ee.Number(year).format('%.0f');
            previous = ee.Image(previous);

            var currentImageBand = ee.String(bandPrefix).cat(year);
            var previousAgeBand = previous.bandNames().reverse().get(0);

            var currentImage = classMask.select([currentImageBand]).unmask(0);
            var previousAge = previous.select([previousAgeBand]);

            var currentAge = previousAge.add(1).multiply(currentImage)
                .rename(ee.String('age_').cat(year));

            return currentAge;

        }, initialAge);

    // Resultado final como imagem
    ages = ee.Image(ages).selfMask();

    return ages;
};

var getClassFrequency = function (image, targetClass, years, bandPrefix) {
    /**
     * Calcula a frequência de uma classe específica em uma imagem de uso do solo.
     * 
     * @param {ee.Image}
     image - A imagem de uso do solo contendo as classes.
     * @param {number}
     targetClass - A classe alvo para a qual a frequência será calculada.
     * @param {Array}
     years - Lista de anos para calcular a frequência.
     * @param {string}
     bandPrefix - Prefixo dos nomes das bandas na imagem.
     * @returns {ee.Image} - Imagem com a frequência da classe alvo para cada ano.
     */
    var classMask = ee.Image(image).eq(targetClass);

    var bands = ee.List(years).map(function (year) {
        year = ee.Number(year).format('%.0f');
        return ee.String(bandPrefix).cat(year);
    });

    var frequencies = classMask.select(bands)
        .reduce(ee.Reducer.sum())
        .selfMask();

    return frequencies;
};

var getNumberOfClasses = function (image, targetClass, years, bandPrefix) {
    /**
     * Calcula o número de estados distintos para uma classe específica em uma imagem de uso do solo.
     * 
     * @param {ee.Image}
     image - A imagem de uso do solo contendo as classes.
     * @param {number}
     targetClass - A classe alvo para a qual o número de estados será calculado.
     * @param {Array}
     years - Lista de anos para calcular o número de estados.
     * @param {string}
     bandPrefix - Prefixo dos nomes das bandas na imagem.
     * @returns {ee.Image} - Imagem com o número de estados distintos da classe alvo.
     */

    var bands = ee.List(years).map(function (year) {
        year = ee.Number(year).format('%.0f');
        return ee.String(bandPrefix).cat(year);
    });

    var numberOfClasses = image.select(bands).reduce(ee.Reducer.countDistinctNonNull());

    return numberOfClasses;
};

var getNumberOfChanges = function (image, years, bandPrefix) {
    /**
     * Calcula o número de mudanças em uma imagem de uso do solo ao longo dos anos.
     *
     * @param {ee.Image}
     image - A imagem de uso do solo contendo as classes.
     * @param {Array}
     years - Lista de anos para calcular o número de mudanças.
     * @param {string}
     bandPrefix - Prefixo dos nomes das bandas na imagem.
     * @returns {ee.Image} - Imagem com o número de mudanças ao longo dos anos.
     */

    var bands = ee.List(years).map(function (year) {
        year = ee.Number(year).format('%.0f');
        return ee.String(bandPrefix).cat(year);
    });

    var changes = image.select(bands)
        .reduce(ee.Reducer.countRuns())
        .subtract(1);

    return changes;
};

var getStableClasses = function (image, years, bandPrefix) {
    /**
     * Calcula a estabilidade das classes em uma imagem de uso do solo.
     * 
     * @param {ee.Image}
     image - A imagem de uso do solo contendo as classes.
     * @param {Array}
     years - Lista de anos para calcular a estabilidade.
     * @param {string}
     bandPrefix - Prefixo dos nomes das bandas na imagem.
     * @returns {ee.Image} - Imagem com a estabilidade da classe alvo ao longo dos anos.
     */
    var image = ee.Image(image);;

    var bands = ee.List(years).map(function (year) {
        year = ee.Number(year).format('%.0f');
        return ee.String(bandPrefix).cat(year);
    });
    
    var numberOfClasses = getNumberOfClasses(image, targetClass, years, bandPrefix);

    var stable = image.select([bands.reverse().get(0)])
        .mask(numberOfClasses.eq(1))
        .selfMask();

    return stable;
};

var getClassLastYear = function (image, targetClass, years, bandPrefix) {
    /**
     * Obtém o último ano de uma imagem de uso do solo.
     * 
     * @param {ee.Image}
     image - A imagem de uso do solo contendo as classes.
     * @param {Array}
     years - Lista de anos para obter o último ano.
     * @param {string}
     bandPrefix - Prefixo dos nomes das bandas na imagem.
     * @returns {ee.Image} - Imagem com o último ano da classe alvo.
     */      

    var image = ee.Image(image);

    var imageYears = years.map(
        function (year) {
            year = ee.Number(year);
            var bandName = ee.String(bandPrefix).cat(year.format('%.0f'));

            var imageYear = image.select([bandName]).eq(ee.Image(targetClass)).multiply(year);
            return imageYear;
        }
    );

    var lastYear = ee.Image(imageYears).reduce(
        ee.Reducer.max()    
    ).selfMask();

    return lastYear;
};

var getAccumulatedClass = function (image, targetClass, years, bandPrefix) {
    /**
     * Calcula a acumulação de uma classe específica em uma imagem de uso do solo.
     *
     * @param {ee.Image}
     image - A imagem de uso do solo contendo as classes.
     * @param {number}
     targetClass - A classe alvo para a qual a acumulação será calculada.
     * @param {Array}
     years - Lista de anos para calcular a acumulação.
     * @param {string}
     bandPrefix - Prefixo dos nomes das bandas na imagem.
     * @returns {ee.Image} - Imagem com a acumulação da classe alvo ao longo dos anos.
     */
    var classMask = ee.Image(image).eq(targetClass);

    var bands = ee.List(years).map(function (year) {
        year = ee.Number(year).format('%.0f');
        return ee.String(bandPrefix).cat(year);
    });

    // deforestation
    var accumulated = image
        .select(bands)
        .mask(classMask)
        .reduce(ee.Reducer.firstNonNull());

    return accumulated;
};

// Exibição da imagem original
Map.addLayer(image, {
    bands: ['classification_2023'],
    min: 0,
    max: 69,
    palette: paletteLulc,
    format: 'png'
}, 'LULC 2023');

// Chamada da função para calcular a idade da classe alvo
var ages = getClassAge(image, targetClass, years, bandPrefix).selfMask();

// Exibição da imagem de idade da classe alvo
Map.addLayer(ages, {
    min: 0,
    max: years.length,
    palette: palette,
    format: 'png'
}, 'Class ' + String(targetClass) + ' Age');

// Chamada da função para calcular a frequência da classe alvo
var frequencies = getClassFrequency(image, targetClass, years, bandPrefix).selfMask();

// Exibição da imagem de frequência da classe alvo
Map.addLayer(frequencies, {
    min: 0,
    max: years.length,
    palette: palette,
    format: 'png'
}, 'Class ' + String(targetClass) + ' Frequency');

// Chamada da função para calcular o número de classes distintas
var numberOfClasses = getNumberOfClasses(image, targetClass, years, bandPrefix).selfMask();

// Exibição da imagem com o número de classes distintas
Map.addLayer(numberOfClasses, {
    min: 0,
    max: 6,
    palette: palette,
    format: 'png'
}, 'Number of Classes');

// Chamada da função para calcular o número de mudanças
var numberOfChanges = getNumberOfChanges(image, years, bandPrefix).selfMask();

// Exibição da imagem com o número de mudanças
Map.addLayer(numberOfChanges, {
    min: 0,
    max: 6,
    palette: palette,
    format: 'png'
}, 'Number of Changes');

// Chamada da função para calcular a estabilidade das classes
var stable = getStableClasses(image, years, bandPrefix).selfMask();

// Exibição da imagem com a estabilidade das classes
Map.addLayer(stable, {
    min: 0,
    max: 69,
    palette: paletteLulc,
    format: 'png'
}, 'Stable Classes');

// Chamada da função para obter o último ano da classe alvo
var lastYear = getClassLastYear(image, targetClass, years, bandPrefix).selfMask();

// Exibição da imagem com o último ano da classe alvo
Map.addLayer(lastYear, {
    min: 1985,
    max: 2023,
    palette: palette,
    format: 'png'
}, 'Class ' + String(targetClass) + ' Last Year');

// Chamada da função para calcular a acumulação da classe alvo
var accumulated = getAccumulatedClass(image, targetClass, years, bandPrefix).selfMask();

// Exibição da imagem com a acumulação da classe alvo
Map.addLayer(accumulated, {
    min: 0,
    max: 69,
    palette: paletteLulc,
    format: 'png'
}, 'Class ' + String(targetClass) + ' Accumulated');
