window.dashExtensions = Object.assign({}, window.dashExtensions, {
    default: {
        function0: function(feature) {
            return {
                color: feature.properties.color,
                weight: 2,
                fillColor: feature.properties.color
            };
        }
    }
});