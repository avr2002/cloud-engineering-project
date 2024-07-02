# Lambda Layers

You can configure your Lambda function to use additional code and content in the form of layers. A layer is a ZIP archive that contains libraries, a custom runtime, or other dependencies. With layers, you can use libraries in your function without needing to include them in your deployment package.

Layers can have orders, and the order determines the precedence of the layers. The layer with the highest order is at the top, and the layer with the lowest order is at the bottom. If a file exists in multiple layers, the file in the layer with the highest order is used.


0
```text
layer-1/
    directory/
        file1.txt  # hello!
        file2.txt  # world!
```

1
```text
layer-2/
    directory/
        file1.txt  # hi
```

In this example, the file `file1.txt` in `layer-2` is used because `layer-2` has a higher order than `layer-1`.