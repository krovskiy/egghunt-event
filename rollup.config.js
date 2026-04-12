import { terser } from '@rollup/plugin-terser';
import obfuscator from 'rollup-plugin-obfuscator';

const input = {
	script: 'src/assets/js/script.js',
	my_eggs: 'src/assets/js/my_eggs.js',
	preview: 'src/assets/js/preview.js',
	rules_timer: 'src/assets/js/rules_timer.js',
	leaderboard: 'src/assets/js/leaderboard.js',
	egg_viewer: 'src/assets/js/egg_viewer.js',
};

export default {
	input,
	output: {
		dir: 'src/assets/dist',
		format: 'esm',
		sourcemap: false,
		entryFileNames: '[name].js',
	},
	plugins: [
		terser({
			format: {
				comments: false,
			},
			compress: {
				passes: 2,
				dead_code: true,
				unsafe_arrows: true,
			},
			mangle: {
				properties: false,
			},
		}),
		obfuscator({
			compact: true,
			controlFlowFlattening: true,
			controlFlowFlatteningThreshold: 0.8,
			deadCodeInjection: true,
			deadCodeInjectionThreshold: 0.2,
			identifierNamesGenerator: 'hexadecimal',
			stringArray: true,
			stringArrayThreshold: 0.75,
			splitStrings: true,
			splitStringsChunkLength: 6,
			selfDefending: true,
		}),
	],
	treeshake: true,
};
