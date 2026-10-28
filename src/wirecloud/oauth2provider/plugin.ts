// OAuth pages use the ordinary plugin/view bundle pipeline.
const OAUTH_PAGE_SCRIPTS: string[] = [
    'js/StyledElements/Utils.js',
    'js/StyledElements/Event.js',
    'js/StyledElements/ObjectWithEvents.js',
    'js/StyledElements/StyledElements.js',
    'js/StyledElements/Container.js',
    'js/StyledElements/Fragment.js',
    'js/StyledElements/GUIBuilder.js',
    'js/StyledElements/Tooltip.js',
    'js/StyledElements/Panel.js',
    'js/StyledElements/Button.js',
    'js/StyledElements/Alert.js',
    'js/oauth2provider/pages.js',
];

export default {
    get_scripts: (view: string): string[] => view === 'oauth2' ? OAUTH_PAGE_SCRIPTS : [],
    scripts_location: 'js',
};
