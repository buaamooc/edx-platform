define(["backbone"], function(Backbone) {
  /**
   * Simple model for an video.
   */
  var Asset = Backbone.Model.extend({
    defaults: {
      display_name: "",
      date_added: "",
      url: "",
      video_size: 0,
      portable_url: ""
    },
  });
  return Asset;
});
