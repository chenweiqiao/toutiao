const glob = require('glob')
const path = require('path')

const config = {
  entry: glob.sync('./src/**/*.js').reduce(
      (entries, entry) => Object.assign(entries, {[entry.split('/').pop().replace('.js', '')]: entry}), {}),

  module: {
    rules: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        use: {
          loader: 'babel-loader',
          options: {
            presets: ['@babel/preset-env']
          }
        }
      },
      {
        test: /\.scss$/,
        use: [
          "style-loader",
           "css-loader",
           "sass-loader"
        ]
      },
      {
        test: /\.css$/,
        use: [ 'style-loader', 'css-loader' ]
      }
    ]
  },

  output: {
    filename: '[name].js',
    path: path.join(__dirname, 'static/dist')
  }
}

module.exports = config
