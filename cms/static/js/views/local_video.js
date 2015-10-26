define(["js/views/baseview", "underscore", "gettext", "common/js/components/views/feedback_prompt",
      "common/js/components/views/feedback_notification"],
    function(BaseView, _, gettext, PromptView, NotificationView) {
var AssetView = BaseView.extend({
  initialize: function() {
    this.template = this.loadTemplate("local-video");
  },
  tagName: "tr",
  events: {
    "click .remove-asset-button": "confirmDelete",
  },

  render: function() {
    this.$el.html(this.template({
      display_name: this.model.get('display_name'),
      date_added: this.model.get('date_added'),
      run: this.model.get('run'),
      url: this.model.get('url'),
      video_size: this.model.get('video_size'),
      portable_url: this.model.get('portable_url')
    }));
    return this;
  },

  confirmDelete: function(e) {
    if(e && e.preventDefault) { e.preventDefault(); }
    var asset = this.model, collection = this.model.collection;
    new PromptView.Warning({
      title: gettext("Delete Video Confirmation"),
      message: gettext("Are you sure you wish to delete this item. It cannot be reversed!\n\nAlso any content that links/refers to this item will no longer work (e.g. broken videos)"),
      actions: {
        primary: {
          text: gettext("Delete"),
          click: function (view) {
            view.hide();
            asset.destroy({
                wait: true, // Don't remove the video from the collection until successful.
                success: function () {
                  new NotificationView.Confirmation({
                    title: gettext("Your video has been deleted."),
                    closeIcon: false,
                    maxShown: 2000
                  }).show();
                }
            });
          }
        },
        secondary: {
          text: gettext("Cancel"),
          click: function (view) {
            view.hide();
          }
        }
      }
    }).show();
  }
});

return AssetView;
}); // end define()
