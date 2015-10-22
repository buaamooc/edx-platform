define(["jquery", "underscore", "gettext", "js/views/baseview", "js/models/local_video", "js/views/paging",
        "js/views/local_video", "js/views/paging_header", "common/js/components/views/paging_footer",
        "js/utils/modal", "common/js/components/utils/view_utils", "common/js/components/views/feedback_notification",
        "text!templates/local-video-library.underscore",
        "jquery.fileupload-process", "jquery.fileupload-validate"],
    function($, _, gettext, BaseView, AssetModel, PagingView, AssetView, PagingHeader, PagingFooter,
             ModalUtils, ViewUtils, NotificationView, asset_library_template) {

        var CONVERSION_FACTOR_MBS_TO_BYTES = 1000 * 1000;

        var AssetsView = BaseView.extend({
            // takes AssetCollection as model

            events : {
                "click .column-sort-link": "onToggleColumn",
                "click .upload-button": "showUploadModal",
            },

            allLabel: 'ALL',


            initialize : function(options) {
                options = options || {};

                BaseView.prototype.initialize.call(this);
                var collection = this.collection;
                this.pagingView = this.createPagingView();
                this.listenTo(collection, 'destroy', this.handleDestroy);
                ViewUtils.showLoadingIndicator();
                // set default file size for uploads via template var,
                // and default to static old value if none exists
                this.uploadChunkSizeInMBs = options.uploadChunkSizeInMBs || 100;
                this.maxFileSizeInMBs = options.maxFileSizeInMBs || 1000;
                this.uploadChunkSizeInBytes = this.uploadChunkSizeInMBs * CONVERSION_FACTOR_MBS_TO_BYTES;
                this.maxFileSizeInBytes = this.maxFileSizeInMBs * CONVERSION_FACTOR_MBS_TO_BYTES;
                this.maxFileSizeRedirectUrl = options.maxFileSizeRedirectUrl || '';
                // error message modal for large file uploads
                this.largeFileErrorMsg = null;
            },

            PagingAssetView: PagingView.extend({
                renderPageItems: function() {
                    var self = this,
                    assets = this.collection,
                    hasAssets = assets.length > 0,
                    tableBody = this.getTableBody();
                    tableBody.empty();
                    if (hasAssets) {
                        assets.each(
                            function(asset) {
                                var view = new AssetView({model: asset});
                                tableBody.append(view.render().el);
                            }
                        );
                    }
                    self.$('.assets-library').toggle(hasAssets);
                    self.$('.no-asset-content').toggle(!hasAssets);
                    return this;
                },

                getTableBody: function() {
                    var tableBody = this.tableBody;
                    if (!tableBody) {
                        ViewUtils.hideLoadingIndicator();

                        // Create the table
                        this.$el.html(_.template(asset_library_template, {}));
                        tableBody = this.$('#asset-table-body');
                        this.tableBody = tableBody;
                        this.pagingHeader = new PagingHeader({view: this, el: $('#asset-paging-header')});
                        this.pagingFooter = new PagingFooter({collection: this.collection, el: $('#asset-paging-footer')});
                        this.pagingHeader.render();
                        this.pagingFooter.render();

                        // Hide the contents until the collection has loaded the first time
                        this.$('.assets-library').hide();
                        this.$('.no-asset-content').hide();
                    }
                    return tableBody;
                },

                onError: function() {
                    ViewUtils.hideLoadingIndicator();
                }
            }),

            createPagingView: function() {
                var pagingView = new this.PagingAssetView({
                    el: this.$el,
                    collection: this.collection
                });
                pagingView.registerSortableColumn('js-asset-name-col', gettext('Name'), 'display_name', 'asc');
                pagingView.registerSortableColumn('js-asset-date-col', gettext('Date Added'), 'date_added', 'desc');
                pagingView.registerSortableColumn('js-asset-size-col', gettext('Video Size'), 'video_size', 'desc');
                pagingView.setInitialSortColumn('js-asset-date-col');
                pagingView.setPage(0);
                return pagingView;
            },

            render: function() {
                this.pagingView.render();
                return this;
            },

            afterRender: function(){
                // Bind events with html elements
                $('li a.upload-button').on('click', _.bind(this.showUploadModal, this));
                $('.upload-modal .close-button').on('click', _.bind(this.hideModal, this));
                $('.upload-modal .choose-file-button').on('click', _.bind(this.showFileSelectionMenu, this));
                return this;
            },

            handleDestroy: function(model) {
                this.collection.fetch({reset: true}); // reload the collection to get a fresh page full of items
                analytics.track('Deleted Video', {
                    'course': course_location_analytics,
                    'id': model.get('url')
                });
            },

            addAsset: function (model) {
                // Switch the sort column back to the default (most recent date added) and show the first page
                // so that the new video is shown at the top of the page.
                this.pagingView.setInitialSortColumn('js-asset-date-col');
                this.pagingView.setPage(0);

                analytics.track('Uploaded a Video', {
                    'course': course_location_analytics,
                    'asset_url': model.get('url')
                });
            },

            onToggleColumn: function(event) {
                var columnName = event.target.id;
                this.pagingView.toggleSortOrder(columnName);
            },

            hideModal: function (event) {
                if (event) {
                    event.preventDefault();
                }
                $('.file-input').unbind('change.startUpload');
                ModalUtils.hideModal();
                if (this.largeFileErrorMsg) {
                  this.largeFileErrorMsg.hide();
                }
            },

            showUploadModal: function (event) {
                var self = this;
                event.preventDefault();
                self.resetUploadModal();
                ModalUtils.showModal();
                $('.modal-cover').on('click', self.hideModal);
                $('.file-input').bind('change', self.startUpload);
                $('.upload-modal .file-chooser').fileupload({
                    dataType: 'json',
                    type: 'POST',
                    maxChunkSize: self.uploadChunkSizeInBytes,
                    autoUpload: true,
                    progressall: function(event, data) {
                        var percentComplete = parseInt((100 * data.loaded) / data.total, 10);
                        self.showUploadFeedback(event, percentComplete);
                    },
                    maxFileSize: self.maxFileSizeInBytes,
                    maxNumberofFiles: 100,
                    done: function(event, data) {
                        self.displayFinishedUpload(data.result);
                    },
                    processfail: function(event, data) {
                        var filename = data.files[data.index].name;
                        var error = gettext("File {filename} exceeds maximum size of {maxFileSizeInMBs} MB")
                                    .replace("{filename}", filename)
                                    .replace("{maxFileSizeInMBs}", self.maxFileSizeInMBs)

                        // disable second part of message for any falsy value,
                        // which can be null or an empty string
                        if(self.maxFileSizeRedirectUrl) {
                            var instructions = gettext("Please follow the instructions here to upload a video elsewhere and link to it: {maxFileSizeRedirectUrl}")
                                    .replace("{maxFileSizeRedirectUrl}", self.maxFileSizeRedirectUrl);
                            error = error + " " + instructions;
                        }

                        self.largeFileErrorMsg = new NotificationView.Error({
                            "title": gettext("Your video could not be uploaded"),
                            "message": error
                        });
                        self.largeFileErrorMsg.show();

                        self.displayFailedUpload({
                            "msg": gettext("Max file size exceeded")
                        });
                    },
                    processdone: function(event, data) {
                        self.largeFileErrorMsg = null;
                    }
                });
            },

            showFileSelectionMenu: function(event) {
                event.preventDefault();
                if (this.largeFileErrorMsg) {
                  this.largeFileErrorMsg.hide();
                }
                $('.file-input').click();
            },

            startUpload: function (event) {
                var file = event.target.value;
                if (!this.largeFileErrorMsg) {
                    $('.upload-modal h1').text(gettext('Uploading'));
                    $('.upload-modal .file-name').html(file.substring(file.lastIndexOf("\\") + 1));
                    $('.upload-modal .choose-file-button').hide();
                    $('.upload-modal .progress-bar').removeClass('loaded').show();
                }
            },

            resetUploadModal: function () {
                // Reset modal so it no longer displays information about previously
                // completed uploads.
                var percentVal = '0%';
                $('.upload-modal .progress-fill').width(percentVal);
                $('.upload-modal .progress-fill').html(percentVal);
                $('.upload-modal .progress-bar').hide();

                $('.upload-modal .file-name').show();
                $('.upload-modal .file-name').html('');
                $('.upload-modal .choose-file-button').text(gettext('Choose Video'));
                $('.upload-modal .embeddable-xml-input').val('');
                $('.upload-modal .embeddable').hide();

                this.largeFileErrorMsg = null;
            },

            showUploadFeedback: function (event, percentComplete) {
                var percentVal = percentComplete + '%';
                $('.upload-modal .progress-fill').width(percentVal);
                $('.upload-modal .progress-fill').html(percentVal);
            },

            displayFinishedUpload: function (resp) {
                var asset = resp.asset;

                $('.upload-modal h1').text(gettext('Upload New Video'));
                $('.upload-modal .embeddable-xml-input').val(asset.portable_url).show();
                $('.upload-modal .embeddable').show();
                $('.upload-modal .file-name').hide();
                $('.upload-modal .progress-fill').html(resp.msg);
                $('.upload-modal .choose-file-button').text(gettext('Load Another Video')).show();
                $('.upload-modal .progress-fill').width('100%');

                this.addAsset(new AssetModel(asset));
            },

            displayFailedUpload: function (resp) {
                $('.upload-modal h1').text(gettext('Upload New Video'));
                $('.upload-modal .embeddable-xml-input').hide();
                $('.upload-modal .embeddable').hide();
                $('.upload-modal .file-name').hide();
                $('.upload-modal .progress-fill').html(resp.msg);
                $('.upload-modal .choose-file-button').text(gettext('Load Another Video')).show();
                $('.upload-modal .progress-fill').width('0%');
            }
        });

        return AssetsView;
    }); // end define();
